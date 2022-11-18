# Sai Advaith Maddipatla 1904223
import sys
from socket import *
import math
import time
from threading import Thread, Lock, Timer

# Define pointers
base = 0
next_sequence_number = 0

class Sender(Thread):
    """
    Thread for Sending packets
    """
    # chunks, "packet_sender", packets_start_idx, packets_end_idx, RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER
    def __init__(self, chunks, socket, start_idx, end_idx, receiver_ip, receiver_port, retransmit = False):
        Thread.__init__(self)
        self.chunks = chunks
        self.socket = socket
        self.start_idx, self.end_idx = start_idx, end_idx
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.retransmit = retransmit

    def format_packet(self, next_seq):
        """
        Add header to a chunk
        """
        if next_seq < len(self.chunks):
            # Header
            seq_number = int.to_bytes(next_seq, 2, 'little')
            if next_seq != len(self.chunks) - 1:
                eof = int.to_bytes(0, 1, 'little')
            else:
                eof = int.to_bytes(1, 1, 'little')

            # Prepare data
            header_i = seq_number + eof
            chunk_i = header_i + self.chunks[next_seq]
            return chunk_i
        else:
            return None

    def run(self):
        # Send
        if self.start_idx < len(self.chunks) or self.end_idx < len(self.chunks):
            for i in range(self.start_idx, self.end_idx):
                chunk_i = self.format_packet(i)
                if chunk_i is not None:
                    try:
                        self.socket.sendto(chunk_i, (self.receiver_ip, self.receiver_port))
                    except:
                        return
        else:
            pass

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
        self.timer_object = None

    def retransmit(self):
        """
        Another thread to retransmit the packet
        """
        global base
        global next_sequence_number
        if (base == next_sequence_number) and base == len(self.chunks):
            return
        # Just in case
        self.timer_object.cancel()
        # Start before retransmit
        self.timer_object = Timer(self.timelimit, lambda: self.retransmit())
        self.timer_object.start()

        # Retransmit
        retransmit_sender = Sender(self.chunks, self.socket, base, next_sequence_number, self.receiver_ip, self.receiver_port, True)
        retransmit_sender.start()

    def clip(self, base, value):
        if base + value > len(self.chunks):
            return len(self.chunks)
        else:
            return base + value
    def run(self):
        """
        Run for the receiving thread
        """
        # Make global
        global next_sequence_number
        global base

        # Every ACK received
        while base < len(self.chunks):
            # Send if window has space
            if (next_sequence_number - base) < self.window_size:
                # Send
                end_idx = self.clip(base, self.window_size)
                packet_sender = Sender(self.chunks, self.socket, base, end_idx, self.receiver_ip, self.receiver_port)
                packet_sender.start()
                # Start timer
                if base == next_sequence_number:
                    if self.timer_object is not None:
                        self.timer_object.cancel()
                    # Start timer
                    self.timer_object = Timer(self.timelimit, self.retransmit)
                    self.timer_object.start()
                # Lock
                lock_nsn = Lock()
                lock_nsn.acquire()
                next_sequence_number = min(end_idx, len(self.chunks))
                lock_nsn.release()

            else:
                # REFUSE
                pass

            # Just receive
            ack_seq, receiver_address = client_socket.recvfrom(2)
            ack_seq = int.from_bytes(ack_seq, 'little')

            # If correct ack received
            window_max = self.clip(base, self.window_size)

            if ack_seq in range(base, window_max):
                lock_receiver = Lock()
                lock_receiver.acquire()
                prev_base = base

                # Shift window
                base = ack_seq + 1
                offset = base - prev_base
                lock_receiver.release()

                if base == next_sequence_number:
                    # Stop timer
                    self.timer_object.cancel()
                else:
                    # Start timer
                    self.timer_object.cancel()
                    self.timer_object = Timer(self.timelimit, self.retransmit)
                    self.timer_object.start()

                # Send new after receiving ack
                new_send_idx = self.clip(next_sequence_number, offset)
                new_sender_thread = Sender(self.chunks, self.socket, next_sequence_number, new_send_idx, self.receiver_ip, self.receiver_port)
                new_sender_thread.start()

                # Lock and update
                lock_nsn = Lock()
                lock_nsn.acquire()
                next_sequence_number = new_send_idx
                lock_nsn.release()

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