# Sai Advaith Maddipatla 1904223

from socket import *
import sys

def update_receive_base(receive_base, received_packet, window_size):
    """
    Move the receive base to the next pointer
    """
    for i in range(receive_base + 1, receive_base + window_size):
        # This means we have not received this yet
        if i not in received_packet.keys():
            break
    return i

def received_prev_packets(received_packet, final_idx):
    """
    Received all old packets
    """
    # Go from 1..n
    for i in range(final_idx):
        # If not in buffer not received
        if i not in received_packet.keys():
            return False
    return True

# Error handling
if len(sys.argv) > 4:
    print("Invalid number of arguments")
    sys.exit()

# Reciever specification
RECEIVER_PORT_NUMBER = int(sys.argv[1])
FILE_NAME = sys.argv[2]
WINDOW_SIZE = int(sys.argv[3])
# Create socket
receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', RECEIVER_PORT_NUMBER))

file_chunks = []

# Parameters for file
CHUNK_SIZE = 1027
file_received = False

# Next sequence number
receive_base = 0

pkt_dict = {}
pkt_received = {}

FINAL_BYTE = 65535
final_sequence_number = None
while True:
    # chunks we should have
    chunk, sender_address = receiver_socket.recvfrom(CHUNK_SIZE)

    # Bytes 1,2 -> seq_no and byte 3 -> eof
    sequence_number, eof = chunk[:2], chunk[2]
    sequence_number = int.from_bytes(sequence_number, 'little')


    # Not duplicate
    # TODO: No knowledge about number of chunks?
    if sequence_number in range(receive_base, receive_base + WINDOW_SIZE):
        # Save chunk
        data = chunk[3:]
        pkt_dict[sequence_number] = data
        pkt_received[sequence_number] = True

        # End of File
        if eof == 1:
            final_sequence_number = sequence_number
        if final_sequence_number is not None and received_prev_packets(pkt_received, final_sequence_number):
            # Send 10 ACKS
            for i in range(10):
                ACK = int.to_bytes(FINAL_BYTE, 2, 'little')
                receiver_socket.sendto(ACK, sender_address)
            break

        # Buffer and send ACK
        ACK = int.to_bytes(sequence_number, 2, 'little')
        print(f"ACK sent {sequence_number}, receiver base = {receive_base}")
        receiver_socket.sendto(ACK, sender_address)
        if sequence_number == receive_base:
            receive_base = update_receive_base(receive_base, pkt_received, WINDOW_SIZE)

    elif sequence_number in range(max(0, receive_base - WINDOW_SIZE), receive_base):
        # Just send an ACK
        ACK = int.to_bytes(sequence_number, 2, 'little')
        print(f"ACK sent {sequence_number}, receiver base = {receive_base}")
        receiver_socket.sendto(ACK, sender_address)
    else:
        pass

receiver_socket.close()

# Sort it out
pkt_dict_keys_sorted = sorted(pkt_dict)

# Store it
for seq in pkt_dict_keys_sorted:
    file_chunks.append(pkt_dict[seq])

# Write file back
write_file = open(FILE_NAME, 'wb')
for chunk in file_chunks:
    write_file.write(chunk)
write_file.close()