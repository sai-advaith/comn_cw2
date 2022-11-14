# Python imports
import sys
import time
from socket import *
import math

# Error handling
if len(sys.argv) > 5:
    print("Invalid number of arguments")
    sys.exit()

# Reciever specification
RECEIVER_IP_ADDRESS = sys.argv[1]
RECEIVER_PORT_NUMBER = int(sys.argv[2])
FILE_NAME = sys.argv[3]
TIMELIMIT = float(sys.argv[4]) / 1000

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

# Send all chunks over except last one
file_transfer_start = time.time()
retransmission = 0
for i in range(len(file_chunks) - 1):
    while True:
        try:
            # Sequence number is 2 bytes
            seq_number = int.to_bytes(i, 2, 'little')
            # EOF is one byte
            eof = int.to_bytes(0, 1, 'little')

            # Prepare data
            header_i = seq_number + eof
            chunk_i = header_i + file_chunks[i]

            client_socket.sendto(chunk_i, (RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER))

            # Set timer
            client_socket.settimeout(TIMELIMIT)

            # wait to receive the ack for the packet
            ack_seq, receiver_address = client_socket.recvfrom(2)
            ack_seq = int.from_bytes(ack_seq, 'little')

            # Ack received!
            if ack_seq == i:
                break
        # Timeout
        except timeout:
            retransmission += 1

# Last packet
i += 1

# Send last packet
while True:
    try:
        # Format last packet
        last_seq_number = int.to_bytes(i, 2, 'little')
        eof = int.to_bytes(1, 1, 'little')
        last_header_i = last_seq_number + eof
        last_chunk_i = last_header_i + file_chunks[i]

        client_socket.sendto(last_chunk_i, (RECEIVER_IP_ADDRESS, RECEIVER_PORT_NUMBER))

        # Set timer
        client_socket.settimeout(TIMELIMIT)

        # wait to receive the ack for the packet
        ack_seq, receiver_address = client_socket.recvfrom(2)
        ack_seq = int.from_bytes(ack_seq, 'little')
        # Ack received!
        if ack_seq == i:
            file_transfer_end = time.time()
            break
    # Timeout
    except:
        retransmission += 1

# Throughput in KBytes/sec
time_to_transfer = file_transfer_end - file_transfer_start
throughput = (FILE_SIZE / time_to_transfer) * 0.001

print(retransmission, throughput)
# Close
client_socket.close()