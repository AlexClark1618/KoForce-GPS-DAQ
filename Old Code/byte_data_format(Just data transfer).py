import socket
import time
import random as rand
import struct

HOST = '134.69.194.204'
#HOST = '134.69.215.139'
PORT = 12345

data_file = 'data_file.txt'

with open(data_file,'w') as f:
    f.write("Req Code; Ch; RF; ID; W#; t_ow mil; t_ow submil; Event #\n")

event_num = 0
while True:
    s = socket.socket()
    s.settimeout(0.5)
    s.connect((HOST, PORT))

    cmd = '1' #Get times #Seems easier to send an integer rather than a letter. Im having a difficult time

    time.sleep(10) #Wait for fake client buffer to fill a bit

    event_num += 1
    ts = int(time.time())

    s.send(f"CMD: {cmd}; T_S: {ts}; Event #: {event_num}\n".encode()) 

    packet_format = '!BBBBBBIII'
    packet_size = struct.calcsize(packet_format)

    # Collect packets until timeout or no more data
    raw_data = bytearray()
    try: #Continually reads data until buffer is empty
        while True:
            chunk = s.recv(1024)
            if not chunk:
                break
            raw_data.extend(chunk)
    except socket.timeout:
        s.connect((HOST, PORT))  # Done receiving

    print(f"Received {len(raw_data)} bytes")

    for i in range(0, len(raw_data), packet_size):
        packet_chunk = raw_data[i:i+packet_size]
        if len(packet_chunk) < packet_size:
            print("Incomplete packet, skipping")
            continue
        data = struct.unpack(packet_format, packet_chunk)
        print("Unpacked:", data)
        with open(data_file, 'a') as f:
            f.write(f'{data}\n')

