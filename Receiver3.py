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

# Parameters for file
CHUNK_SIZE = 1027
file_received = False

# Next sequence number
expected_next_seq = 0

while True:
    # chunks we should have
    chunk, sender_address = receiver_socket.recvfrom(CHUNK_SIZE)

    # Bytes 1,2 -> seq_no and byte 3 -> eof
    sequence_number, eof = chunk[:2], chunk[2]
    sequence_number = int.from_bytes(sequence_number, 'little')

    # Not duplicate
    if sequence_number == expected_next_seq:
        # Save chunk
        data = chunk[3:]
        file_chunks.append(data)

        # End of File
        if eof == 1:
            # Send 10 ACKS
            from time import sleep
            for i in range(10):
                ACK = int.to_bytes(expected_next_seq, 2, 'little')
                receiver_socket.sendto(ACK, sender_address)
                # sleep(0.05)
            break

        ACK = int.to_bytes(expected_next_seq, 2, 'little')
        print(f"ACK {expected_next_seq} sent")
        receiver_socket.sendto(ACK, sender_address)
        expected_next_seq += 1
    else:
        # Cumulative ACK
        if expected_next_seq > 0:
            ACK = int.to_bytes(expected_next_seq - 1, 2, 'little')
            print(f"ACK {expected_next_seq} sent")
            receiver_socket.sendto(ACK, sender_address)

receiver_socket.close()

# Write file back
write_file = open(FILE_NAME, 'wb')
for chunk in file_chunks:
    write_file.write(chunk)
write_file.close()