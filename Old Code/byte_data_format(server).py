import socket
import time
import random as rand
import struct

#HOST = '134.69.194.204'
HOST = '134.69.215.139'
PORT = 12345

data_file = 'data_file.txt'

with open(data_file,'w') as f:
    f.write("Req Code; Ch; RF; ID; W#; t_ow mil; t_ow submil; Event #\n")

event_num = 0
def request_func(cmd):
    global event_num
    s = socket.socket()

    s.connect((HOST, PORT))

    if cmd == '1': #Get times #Seems easier to send an integer rather than a letter. Im having a difficult time 
        event_num += 1
        ts = int(time.time())

        time.sleep(10) #Wait for fake client buffer to fill a bit

        s.send(f"CMD: {cmd}; T_S: {ts}; Event #: {event_num}\n".encode())

        #data = s.recv(1024).decode().splitlines()[0] #Recieves data from esp32
        '''
        raw_data = s.recv(1024)
        data = struct.unpack('!BBBBIII', raw_data)
        '''
        packet_format = '!BBBBBBIII'
        packet_size = struct.calcsize(packet_format)

        time.sleep(1)
        raw_data = s.recv(1024)  # could contain multiple packets
        print(f"Received {len(raw_data)} bytes")

        for i in range(0, len(raw_data), packet_size):
            packet_chunk = raw_data[i:i+packet_size]
            if len(packet_chunk) < packet_size:
                print("Incomplete packet, skipping")
                continue
            data = struct.unpack(packet_format, packet_chunk)
            print("Unpacked:", data)
            # Write `unpacked` to your data file here
            
            with open(data_file, 'a') as f:
                f.write(f'{data}\n')
        '''
        for line in data:
            fields = line.split(',')
            inst = fields[0]            # e.g., 'T'
            ch = int(fields[1])         # e.g., 1
            RF = fields[2]              # e.g., 'F'
            ID = int(fields[3])         # e.g., 14
            timestamps = [int(x) for x in fields[4:-1]]
            event_num = int(fields[-1])

            print(f"inst: {inst}, ch: {ch}, RF: {RF}, ID: {ID}, ts: {timestamps}, event_num: {event_num}")
        '''
    if cmd == 'M': #Get Esp Mac address
        s.send(f"CMD: {cmd}\n".encode())

        data = s.recv(1024).decode().splitlines()[0]
    if cmd == 'H': #Check connection
        s.send(f"CMD: {cmd}\n".encode())

        data = s.recv(1024).decode().splitlines()[0]
    #data = s.recv(1024).decode().splitlines() #Recieves data from esp32

if __name__ == "__main__":

    for i in range(10):
        request_func('1')
        time.sleep(1)
    """last_time = time.time()
    if (time.time() - last_time) > 1:
        request_func('1')
        last_time = time.time()"""
    