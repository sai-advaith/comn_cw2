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
while True:
    # chunks we should have
    chunk, sender_address = receiver_socket.recvfrom(CHUNK_SIZE)
    # Bytes 1,2 -> seq_no and byte 3 -> eof
    sequence_number, eof = chunk[:2], chunk[2]
    sequence_number = int.from_bytes(sequence_number, 'little')
    ACK = int.to_bytes(sequence_number, 2, 'little')
    receiver_socket.sendto(ACK, sender_address)
    data = chunk[3:]
    file_chunks.append(data)

    # End of File
    if eof == 1:
        break

receiver_socket.close()
# Write file back
write_file = open(FILE_NAME, 'wb')
for chunk in file_chunks:
    write_file.write(chunk)
write_file.close()