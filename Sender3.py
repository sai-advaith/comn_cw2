import sys
from socket import *
import math
import time
from threading import Thread, Lock, Timer


# Define pointers
base = 0
next_sequence_number = 0

# Dictionary
timer_object = None

class Sender(Thread):
    """
    Thread for Sending packets
    """
    def __init__(self, timeout, chunks, name, window_size, socket, receiver_ip, receiver_port):
        Thread.__init__(self)
        self.timeout = timeout
        self.chunks = chunks
        self.name = name
        self.window_size = window_size
        self.socket = socket
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port

    def format_packet(self, next_seq):
        """
        Add header to a chunk
        """
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

    def run(self):
        # Set global
        global base
        global next_sequence_number
        global timer_object

        # Send
        while next_sequence_number < len(self.chunks):
            # Window is full
            if (next_sequence_number - base) >= self.window_size:
                pass
            else:
                # Get chunk to send
                i = next_sequence_number
                chunk_i = self.format_packet(i)
                self.socket.sendto(chunk_i, (self.receiver_ip, self.receiver_port))
                print(f"packet {i} sent")
                if base == next_sequence_number:
                    timer_object = TimerThread(self.timeout, "timer")
                    # Start timer
                    timer_object.start()

                # Lock
                lock_sender = Lock()
                lock_sender.acquire()

                # Lock when updating this
                next_sequence_number += 1
                print(f"base = {base}, next sequence number = {next_sequence_number}")
                # Lock release
                lock_sender.release()
        
class TimerThread(Thread):
    """
    Thread for maintaining a Timeout
    """
    def __init__(self, timeout, name):
        Thread.__init__(self)
        self.timeout = timeout
        self.name = name
        self.clock = Timer(self.timeout, self.update)
    def update(self):
        """
        After transmit, move next_sequence_number pointer
        """
        global base
        global next_sequence_number

        # Lock
        lock_timer = Lock()
        lock_timer.acquire()
        print("TIMEOUT")
        next_sequence_number = base
        print(f"base = {base}, next sequence number = {next_sequence_number}\n")
        lock_timer.release()

    def run(self):
        """
        Start the timer
        """
        # Start timeout
        print("TIMER STARTED")
        self.clock.start()

    def stop(self):
        """
        Kill it
        """
        print("TIMER STOPPED")
        self.clock.cancel()

class Receiver(Thread):
    """
    Thread for receiving ACKs
    """
    def __init__(self, timeout, chunks, name, window_size, socket, receiver_ip, receiver_port):
        Thread.__init__(self)
        self.timeout = timeout
        self.chunks = chunks
        self.name = name
        self.window_size = window_size
        self.socket = socket
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port

    def run(self):
        """
        Run for the receiving thread
        """
        # Make global
        global next_sequence_number
        global base
        global timer_object

        # Every ACK received
        while base < len(self.chunks):
            # Receive
            ack_seq, receiver_address = client_socket.recvfrom(2)
            ack_seq = int.from_bytes(ack_seq, 'little')

            # If correct ack received
            if ack_seq in range(base, base + self.window_size):
                lock_receiver = Lock()
                lock_receiver.acquire()

                # Shift window
                print(f"ACK {ack_seq} received")
                base = ack_seq + 1
                print(f"base = {base}, next sequence number = {next_sequence_number}\n")
                lock_receiver.release()
                if base == next_sequence_number:
                    timer_object.stop()
                else:
                    # Start timer
                    timer_object.stop()
                    timer_object = TimerThread(self.timeout, "timer")
                    timer_object.start()
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

# Important threads
sender_thread = Sender(TIMELIMIT, chunks, "packet_sender", WINDOW_SIZE, client_socket, RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER)
ack_receiver_thread = Receiver(TIMELIMIT, chunks, "ack_receiver", WINDOW_SIZE, client_socket, RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER)

# Start them
sender_thread.start()
ack_receiver_thread.start()

# Join
sender_thread.join()
ack_receiver_thread.join()

# Close socket
client_socket.close()