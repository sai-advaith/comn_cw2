from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet.tcp import TCP_SYN
from ryu.lib.packet.tcp import TCP_FIN
from ryu.lib.packet.tcp import TCP_RST
from ryu.lib.packet.tcp import TCP_ACK
from ryu.lib.packet.ether_types import ETH_TYPE_IP, ETH_TYPE_ARP

class L4Lb(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4Lb, self).__init__(*args, **kwargs)
        self.ht = {} # {(<sip><vip><sport><dport>): out_port, ...}
        self.vip = '10.0.0.10'
        self.dips = ('10.0.0.2', '10.0.0.3')
        self.dmacs = ('00:00:00:00:00:02', '00:00:00:00:00:03')
        #
        # write your code here, if needed
        self.counter = 0
        self.cmac = '00:00:00:00:00:01'
        self.cip = '10.0.0.1'
        #

    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        return out

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        acts = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, psr.OFPMatch(), acts)

    def add_flow(self, dp, prio, match, acts, buffer_id=None):
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        bid = buffer_id if buffer_id is not None else ofp.OFP_NO_BUFFER
        ins = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, acts)]
        mod = psr.OFPFlowMod(datapath=dp, buffer_id=bid, priority=prio,
                                match=match, instructions=ins)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port, pkt = (msg.match['in_port'], packet.Packet(msg.data))
        dp = msg.datapath
        ofp, psr, did = (dp.ofproto, dp.ofproto_parser, format(dp.id, '016d'))
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        #
        # write your code here, if needed
        acts = []
        #
        iph = pkt.get_protocols(ipv4.ipv4)
        tcph = pkt.get_protocols(tcp.tcp)
        #
        # write your code here
        arph = pkt.get_protocols(arp.arp)
        # print(iph, arph, tcp)
        tcp_ipv4_pkt = (len(tcph) != 0) and (len(iph) != 0)
        arp_pkt = (len(arph) != 0)

        if tcp_ipv4_pkt:
            frame_tuple = (iph[0].src, iph[0].dst, tcph[0].src_port, tcph[0].dst_port)

            # Configure the frame
            if in_port != 1:
                out_port = 1
                acts = [psr.OFPActionSetField(ipv4_src = self.vip),
                        psr.OFPActionOutput(out_port)]

            else:
                self.counter += 1
                if self.counter % 2 == 1:
                    out_port = 2
                    # Send packet to port 2 (server 1) and manipulate addresses
                    # Send to server 1
                    acts = [psr.OFPActionSetField(eth_dst = self.dmacs[0]),
                            psr.OFPActionSetField(ipv4_dst = self.dips[0]),
                            psr.OFPActionOutput(out_port)]

                else:
                    out_port = 3
                    # Send packet to port 3 (server 2) and manipulate addresses
                    # Send to server 2
                    acts = [psr.OFPActionSetField(eth_dst = self.dmacs[1]),
                            psr.OFPActionSetField(ipv4_dst = self.dips[1]),
                            psr.OFPActionOutput(out_port)]

            # Add if it does not exist
            if frame_tuple not in self.ht:
                self.ht[frame_tuple] = out_port

            # Match for protocol
            match = psr.OFPMatch(
                in_port=in_port,
                eth_type = ETH_TYPE_IP,
                ip_proto=in_proto.IPPROTO_TCP,
                ipv4_src=iph[0].src,
                ipv4_dst=iph[0].dst,
                tcp_src=tcph[0].src_port,
                tcp_dst=tcph[0].dst_port
            )

            # Add flow to switch if tcp packet
            self.add_flow(dp, 1, match, acts, msg.buffer_id)

            # Buffer check
            if msg.buffer_id != ofp.OFP_NO_BUFFER:
                return

        elif arp_pkt:
            # Client
            if in_port == 1:
                self.counter += 1
                if self.counter % 2 == 1:
                    arp_reply_pkt = packet.Packet()
                    # Make changes to ip and mac
                    self.cmac, self.cip = arph[0].src_mac, arph[0].src_ip
                    ethernet_pkt = ethernet.ethernet(self.cmac, self.dmacs[0], ETH_TYPE_ARP)
                    arp_pkt = arp.arp_ip(
                        arp.ARP_REPLY,
                        src_mac=self.dmacs[0],
                        src_ip=self.vip,
                        dst_mac=self.cmac,
                        dst_ip=self.cip
                    )
                    arp_reply_pkt.add_protocol(ethernet_pkt)
                    arp_reply_pkt.add_protocol(arp_pkt)
                    # Send reply packet
                    out = self._send_packet(dp, in_port, arp_reply_pkt)
                    dp.send_msg(out)
                else:
                    arp_reply_pkt = packet.Packet()
                    # Make changes to ip and mac
                    self.cmac, self.cip = arph[0].src_mac, arph[0].src_ip
                    ethernet_pkt = ethernet.ethernet(self.cmac, self.dmacs[1], ETH_TYPE_ARP)
                    arp_pkt = arp.arp_ip(
                        arp.ARP_REPLY,
                        src_mac=self.dmacs[1],
                        src_ip=self.vip,
                        dst_mac=self.cmac,
                        dst_ip=self.cip
                    )
                    arp_reply_pkt.add_protocol(ethernet_pkt)
                    arp_reply_pkt.add_protocol(arp_pkt)
                    # Send reply packet
                    out = self._send_packet(dp, in_port, arp_reply_pkt)
                    dp.send_msg(out)
            else:
                arp_reply_pkt = packet.Packet()

                # Make changes to ip and mac
                ethernet_pkt = ethernet.ethernet(self.dmacs[in_port - 2], self.cmac, ETH_TYPE_ARP)
                arp_pkt = arp.arp(hwtype=1,
                                    proto=0x0800,
                                    hlen=6,
                                    plen=4,
                                    opcode=2,
                                    src_mac=self.cmac,
                                    src_ip=self.cip,
                                    dst_mac=self.dmacs[in_port - 2],
                                    dst_ip=self.dips[in_port - 2])
                arp_reply_pkt.add_protocol(ethernet_pkt)
                arp_reply_pkt.add_protocol(arp_pkt)

                # Send reply packet
                out = self._send_packet(dp, in_port, arp_reply_pkt)
                dp.send_msg(out)
            return
        else:
            # Drop
            acts = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
        #
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                               in_port=in_port, actions=acts, data=data)
        dp.send_msg(out)
