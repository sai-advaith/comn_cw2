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

print("Waiting for file....")
file_chunks = []

CHUNK_SIZE = 1027
file_received = False
while True:
    # chunks we should have
    chunk, sender_address = receiver_socket.recvfrom(CHUNK_SIZE)

    # Bytes 1,2 -> seq_no and byte 3 -> eof
    sequence_number, eof = chunk[:2], chunk[2]
    data = chunk[2:]
    file_chunks.append(data)

    # Debug line
    receiver_socket.sendto(f"Sequence number {sequence_number} received")

    # End of File
    if eof[0] == 1:
        break

# Write file back
write_file = open('receiver_test.jpg', 'wb')
for chunk in file_chunks:
    write_file.write(chunk)
write_file.close()