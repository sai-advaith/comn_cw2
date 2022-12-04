from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet.ether_types import ETH_TYPE_IP

class L4State14(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4State14, self).__init__(*args, **kwargs)
        self.ht = set()

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
        # write your code here
        dst, src = (eth.dst, eth.src)

        actions = []

        # Check if tcp/ipv4 packet
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ipv4_packet = pkt.get_protocol(ipv4.ipv4)
        tcp_icpv4_pkt = (tcp_pkt is not None) and (ipv4_packet is not None)

        # if not tcp packet we just let it pass
        if tcp_icpv4_pkt:
            illegal_flags = tcp_pkt.has_flags(tcp.TCP_SYN, tcp.TCP_FIN) or tcp_pkt.has_flags(tcp.TCP_SYN, tcp.TCP_RST) or tcp_pkt.bits == 0
            # check for tcp flags
            if illegal_flags:
                # Action
                actions = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
            else:
                # Match for protocol
                match = psr.OFPMatch(
                    in_port=in_port,
                    ip_proto=ipv4_packet.proto,
                    ipv4_src=ipv4_packet.src,
                    ipv4_dst=ipv4_packet.dst,
                    tcp_src=tcp_pkt.src_port,
                    tcp_dst=tcp_pkt.dst_port
                )
                if in_port == 1:
                    # Frame tuple
                    # (<srcip>, <dstip>, <srcport>, <dstport>)
                    frame_tuple = (ipv4_packet.src, ipv4_packet.dst, tcp_pkt.src_port, tcp_pkt.dst_port)

                    # Add flow to switch if tcp packet
                    out_port = 2
                    actions = [psr.OFPActionOutput(out_port)]
                    self.add_flow(dp, 1, match, actions, msg.buffer_id)

                    self.ht.add(frame_tuple)
                    # Buffer check
                    if msg.buffer_id != ofp.OFP_NO_BUFFER:
                        return

                if in_port == 2:
                    # Frame tuple
                    # (<srcip>, <dstip>, <srcport>, <dstport>)
                    frame_tuple_check = (ipv4_packet.dst, ipv4_packet.src, tcp_pkt.dst_port, tcp_pkt.src_port)
                    if frame_tuple_check not in self.ht:
                        actions = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
                    else:
                        out_port = 1
                        actions = [psr.OFPActionOutput(out_port)]
                        self.add_flow(dp, 1, match, actions, msg.buffer_id)

                        # Buffer check
                        if msg.buffer_id != ofp.OFP_NO_BUFFER:
                            return
        else:
            # Configure actions based on input port
            if in_port == 2:
                out_port = 1
            elif in_port == 1:
                out_port = 2

            # Configure actions based on input port
            actions = [psr.OFPActionOutput(out_port)]

        # Forward the packet
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                               in_port=in_port, actions=actions, data=data)
        dp.send_msg(out)
