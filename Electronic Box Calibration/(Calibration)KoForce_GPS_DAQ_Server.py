import socket
import select
import struct
import os
import re
from datetime import datetime
import gzip
import shutil
import time

HOST = '0.0.0.0'
PORT = 12345

# Format: 
PACKET_FORMAT = "!IIIIIIIII"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

# Create the server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
server.setblocking(False)

print(f"Server listening on {HOST}:{PORT}")

sockets = [server]  # includes all connected sockets
clients = {}        # map client socket -> {'buffer': bytearray, 'id': int}

connection_log = 'connection_log.txt'
error_log = 'error_log.txt'

class RotatingFileWriter:
    def __init__(self, base_name="output", ext=".txt", max_size=1024, gzip_files=True, header = ""):
        self.base_name = base_name
        self.ext = ext
        self.max_size = max_size
        self.gzip_files = gzip_files
        self.date = datetime.now().strftime("%Y%m%d")
        self.run_number = self._get_next_run_number()
        self.cycle_number = 1
        self.current_size = 0
        self.header = header
        self.open_new_file()

    def _get_next_run_number(self):
        """Find the next available run number across all files."""
        run_pattern = re.compile(
            rf"{self.base_name}_(\d+)_run(\d+)_cycle\d+{self.ext}$"
        )
        max_run = 0
        for fname in os.listdir("."):
            match = run_pattern.match(fname)
            if match:
                run_num = int(match.group(2))
                max_run = max(max_run, run_num)
        return max_run + 1

    def open_new_file(self):
        if hasattr(self, "file") and self.file:
            self._close_and_gzip()
        self.filename = (
            f"{self.base_name}_{self.date}_run{self.run_number}_cycle{self.cycle_number}{self.ext}"
        )
        self.file = open(self.filename, "w", buffering=1024*1024)
        if self.header:
            self.file.write(self.header + "\n") 
            self.current_size = len(self.header) + 1
        else:
            self.current_size = 0
        print(f"[INFO] Opened {self.filename}")
        self.cycle_number += 1
        time.sleep(1)

    def _close_and_gzip(self):
        """Close the current file and optionally gzip it."""
        self.file.close()
        if self.gzip_files:
            gz_filename = self.filename + ".gz"
            with open(self.filename, 'rb') as f_in, gzip.open(gz_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(self.filename)  # remove original uncompressed file
            print(f"[INFO] Compressed {self.filename} -> {gz_filename}")

    def write(self, data: str):
        encoded = data.encode()
        size = len(encoded)
        if self.current_size + size > self.max_size:
            self.open_new_file()
        self.file.write(data)
        self.current_size += size
        print(self.current_size)

    def close(self):
        if self.file:
            self._close_and_gzip()

HEADER = "Req Code; ID; RF; Cal; Ch, W#; t_ow mil; t_ow submil; Event"
writer = RotatingFileWriter(base_name="gps_daq", ext=".txt", max_size=1024*1024, header = HEADER)  # 1 MB max

with open('connection_log.txt', 'w') as log:
    pass
with open('error_log.txt', 'w') as log:
    pass

try:
    while True:
        
        readable, _, _ = select.select(sockets, [], [], 0.1)

        for s in readable:
            if s is server:
                client_socket, addr = server.accept()
                client_socket.setblocking(False)
                sockets.append(client_socket)
                clients[client_socket] = bytearray()
                print(f"New ESP32 connected from {addr}")
                with open('connection_log.txt', 'a') as log:
                    log.write(f"{time.time()}: Reconnected from {addr}\n")

            else:

                try:
                    peek = s.recv(4096, socket.MSG_PEEK)

                    if len(peek)>0:
                        data = s.recv(4096)
                        
                        #print("data recieved")
                        #Need new error handling
                        """if not data:
                            raise ConnectionResetError"""

                        clients[s].extend(data)

                        # Process all complete 2-byte packets
                        while len(clients[s]) >= PACKET_SIZE:
                            packet = clients[s][:PACKET_SIZE]
                            clients[s] = clients[s][PACKET_SIZE:]

                            #Unpacks data
                            inst, ID, RF, Cal, ch, w_num, ms, sub_ms, event_num = struct.unpack(PACKET_FORMAT, packet)
                            
                            #Should write all BH data to borehole first. Maybe have another if below.
                            #ID == 200 for GPS test
                            

                            # #Dealing with encoding pulses
                            # if ID == 200 and ch == 1 and abs(ms - temp_BH_ts_ms) < 1000:
                            #     print(f"Encoding From BH ESP: {inst, ID, RF, Cal, ch, w_num, ms, sub_ms, event_num}")
                            #     with open(data_file,'a') as f:
                            #         f.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}, {sub_ms}; {event_num}\n")
                            #         print("Encoding BH data written to file")
                            
                            # else:
                            #     print('No encoding signal')
                            #     pass

                            if ID == 48:
                                writer.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}\n")
                                print("BH data written to file")
                                
                                if ch == 0 and RF == 0: #Measuring time from rise                                
                                    for client_sock in clients:
                                        if client_sock != s: #Broadcasts BH timestamp to all other clients except sender
                                            try:
                                                
                                                broadcast_format = '!IIIII'
                                                broadcast_packet = struct.pack(broadcast_format, inst, w_num, ms, sub_ms, event_num)
                                                broadcast = client_sock.send(broadcast_packet)
                                                
                                                #broadcast = client_sock.send(f"CMD: {inst}; T_S: {[w_num, ms, sub_ms]}; Event #: {event_num}\n".encode())
                                                
                                                print(f'Request for data sent:{broadcast}')

                        
                                                    #Add error handling to close file properly 
                                            except Exception as e:
                                                print(f"Error sending to {client_sock}: {e}")
                                                pass

                            if ID != 48: #For other boreholes
                                writer.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}\n")
                                print("AS data written to file")
                            
                except (ConnectionResetError, BrokenPipeError):
                    print("Client disconnected")
                    sockets.remove(s)
                    s.close()
                    del clients[s]

except KeyboardInterrupt:
    print("DAQ Stopped")

finally:
    writer.close()