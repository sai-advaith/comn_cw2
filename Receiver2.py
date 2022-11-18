# Sai Advaith Maddipatla 1904223

from socket import *
import sys

# Error handling
if len(sys.argv) > 3:
    print("Invalid number of arguments")
    sys.exit()

# Reciever specification
RECEIVER_PORT_NUMBER = int(sys.argv[1])
FILE_NAME = sys.argv[2]

# Create socket
receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', RECEIVER_PORT_NUMBER))

file_chunks = []

CHUNK_SIZE = 1027
file_received = False
received_seq = []

# TODO:
# Keep track of last sequence number and make sure it increements by 1

while True:
    # chunks we should have
    chunk, sender_address = receiver_socket.recvfrom(CHUNK_SIZE)

    # Bytes 1,2 -> seq_no and byte 3 -> eof
    sequence_number, eof = chunk[:2], chunk[2]
    sequence_number = int.from_bytes(sequence_number, 'little')

    # Not duplicate
    if sequence_number not in received_seq:
        # Save chunk
        received_seq.append(sequence_number)
        data = chunk[3:]
        file_chunks.append(data)

        # End of File
        if eof == 1:
            # Send 10 ACKS
            for i in range(10):
                ACK = int.to_bytes(sequence_number, 2, 'little')
                receiver_socket.sendto(ACK, sender_address)
            break

    ACK = int.to_bytes(sequence_number, 2, 'little')
    receiver_socket.sendto(ACK, sender_address)

receiver_socket.close()

# Write file back
write_file = open(FILE_NAME, 'wb')
for chunk in file_chunks:
    write_file.write(chunk)
write_file.close()