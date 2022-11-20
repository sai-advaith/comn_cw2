# Sai Advaith Maddipatla 1904223
import sys
from socket import *
import math
import time
from threading import Thread, Lock, Timer

# Define pointers
base = 0
next_sequence_number = 0

sequence_number_thread = {}
send_hash = {}
ack_hash = {}

class Sender(Thread):
    """
    Thread for Sending packets
    """
    # chunks, "packet_sender", packets_start_idx, packets_end_idx, RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER
    def __init__(self, chunk, timelimit, socket, receiver_ip, receiver_port, sequence_number):
        Thread.__init__(self)
        self.sequence_number = sequence_number
        self.chunk = chunk
        self.timelimit = timelimit
        self.socket = socket
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.timer = Timer(self.timelimit, self.retransmit)

    def retransmit(self):
        """
        Retransmit sequence number packet
        """
        print("Timeout")
        global sequence_number_thread
        retransmit_lock = Lock()
        retransmit_lock.acquire()

        self.stop_timer()
        resender_thread = Sender(self.chunk, self.timelimit, self.socket, self.receiver_ip, self.receiver_port, self.sequence_number)
        sequence_number_thread[self.sequence_number] = resender_thread
        # re-Send the packet
        resender_thread.start()
        print(f"resending {self.sequence_number}")

        retransmit_lock.release()
        
    def run(self):
        # Send the packets
        try:
            print(f"Sending sequence number {self.sequence_number}")
            self.socket.sendto(self.chunk, (self.receiver_ip, self.receiver_port))
            # Send packet and start timer
            send_timer_lock = Lock()
            send_timer_lock.acquire()

            if self.timer.is_alive():
                self.stop_timer()
            self.timer.start()

            send_timer_lock.release()
        except OSError:
            self.stop_timer()
            return

    def stop_timer(self):
        """
        Wrapper to stop the timer
        """
        print(f"killing thread # {self.sequence_number}")
        # Cancel timer called when we get ack
        self.timer.cancel()

class Receiver(Thread):
    """
    Thread for receiving ACKs
    """
    def __init__(self, timelimit, chunks, window_size, socket, receiver_ip, receiver_port):
        Thread.__init__(self)
        self.timelimit = timelimit
        self.chunks = chunks
        self.window_size = window_size
        self.socket = socket
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.final_idx = 65535

    def format_packet(self, i, chunk, eof):
        """
        Add header to a chunk
        """
        # Header
        seq_number = int.to_bytes(i, 2, 'little')
        if eof:
            eof_byte = int.to_bytes(1, 1, 'little')
        else:
            eof_byte = int.to_bytes(0, 1, 'little')

        # Prepare data
        header_i = seq_number + eof_byte
        chunk_i = header_i + chunk
        return chunk_i

    def clear_threads(self):
        """
        Clear all threads
        """
        global sequence_number_thread
        # Kill the timer
        for thread in sequence_number_thread.values():
            thread.stop_timer()

    def clip(self, base, value):
        if base + value > len(self.chunks):
            return len(self.chunks)
        else:
            return base + value
    def get_next_base(self, base):
        """
        Update base to get to next un-ACK'd packet
        """
        global ack_hash
        global send_hash
        for j in range(base + 1, min(len(self.chunks), base + self.window_size)):
            # Find the first sent packet which has not been ACK'd
            if not ack_hash[j] and send_hash[j]:
                break
        return j
    def send_on_receipt(self, offset, prev_base):
        global ack_hash
        global send_hash
        global sequence_number_thread

        j = 0
        while j < offset:
            idx = prev_base + self.window_size + j
            if idx not in send_hash.keys() and idx < len(self.chunks):          
                chunk_j = self.format_packet(idx, self.chunks[idx], idx == len(self.chunks) - 1)
                packet_sender = Sender(chunk_j, self.timelimit, self.socket, self.receiver_ip, self.receiver_port, idx)
                packet_sender.start()

                # Lock before manipulating sent variable

                # Packet sent but not yet acked
                send_hash[idx] = True
                ack_hash[idx] = False

                # Keep track of that thread
                sequence_number_thread[idx] = packet_sender
                j += 1
            else:
                pass
    def run(self):
        """
        Run for the receiving thread
        """
        # Make global
        global base
        global sequence_number_thread
        global send_hash
        global ack_hash

        # Every ACK received
        while base < len(self.chunks):
            # Send
            # TODO: Do this in sep thread?
            for i in range(base, min(len(self.chunks), base + self.window_size)):    
                # Send packet
                if not i in send_hash.keys():
                    chunk_i = self.format_packet(i, self.chunks[i], i == len(self.chunks) - 1)
                    packet_sender = Sender(chunk_i, self.timelimit, self.socket, self.receiver_ip, self.receiver_port, i)
                    packet_sender.start()

                    # Lock before manipulating sent variable
                    pkt_send_lock = Lock()
                    pkt_send_lock.acquire()

                    # Packet sent but not yet acked
                    send_hash[i] = True
                    ack_hash[i] = False

                    # Keep track of that thread
                    sequence_number_thread[i] = packet_sender

                    # Done - release lock
                    pkt_send_lock.release()
                else:
                    pass

            # Just receive
            ack_seq, receiver_address = client_socket.recvfrom(2)
            print(f"ack received = {ack_seq}")
            ack_seq = int.from_bytes(ack_seq, 'little')
            if ack_seq == self.final_idx:
                self.clear_threads()
                return

            # If correct ack received
            window_max = self.clip(base, self.window_size)

            if base <= ack_seq < window_max:
                lock_update = Lock()
                lock_update.acquire()
                prev_base = base
                if ack_seq == base:
                    # Shift window
                    ack_hash[ack_seq] = True
                    sequence_number_thread[ack_seq].stop_timer()
                else:
                    # Mark received and stop the timer
                    ack_hash[ack_seq] = True
                    sequence_number_thread[ack_seq].stop_timer()

                print(f"update base = {base}")
                # Done with the lock
                offset = base - prev_base
                self.send_on_receipt(offset, prev_base)
                base = self.get_next_base(base)
                # resend right after ack
                lock_update.release()
            else:
                pass

# Error handling
if len(sys.argv) > 6:
    print("Invalid number of arguments")
    sys.exit()

# Input argument specification
RECEIVER_IP_ADDRESS = sys.argv[1]
RECEIVER_PORT_NUMBER = int(sys.argv[2])
FILE_NAME = sys.argv[3]
TIMELIMIT = float(sys.argv[4]) / 1000
WINDOW_SIZE = int(sys.argv[5])

# Prepare file chunks
CHUNK_SIZE = 1024
file_chunks = []

# Splite the file into chunks
FILE_SIZE = 0
with open(FILE_NAME, 'rb') as file:
    chunk = file.read(CHUNK_SIZE)
    file_chunks.append(chunk)
    while chunk:
        chunk = file.read(CHUNK_SIZE)
        FILE_SIZE += len(chunk)
        file_chunks.append(chunk)

# Last one is empt
chunks = file_chunks[:-1]

# Initialize socket
client_socket = socket(AF_INET, SOCK_DGRAM)

# Important thread
ack_receiver_thread = Receiver(TIMELIMIT, chunks, WINDOW_SIZE, client_socket, RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER)

# Start them
file_transfer_start = time.time()
ack_receiver_thread.start()

# Join
ack_receiver_thread.join()
file_transfer_end = time.time()

time_to_transfer = file_transfer_end - file_transfer_start
throughput = int((FILE_SIZE / time_to_transfer) * 0.001)
print(throughput)

# Close socket
client_socket.close()