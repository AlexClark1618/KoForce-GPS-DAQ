import socket
import select
import struct
import os
import re
from datetime import datetime, timedelta
import gzip
import shutil
import time
import traceback

#Changelog:
    #9/24/25- Added server auto restart on uncaught errors; Added better error handling from broadcasting; 
    #Server may have been building up empty sockets leading to the broken pipe errors

HOST = '0.0.0.0'
PORT = 12345

# Data Format: 
PACKET_FORMAT = "!iiiiiiiiii"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

# class RotatingFileWriter:
#     def __init__(self, base_name="output", ext=".txt", max_size=1024, gzip_files=False, header = ""):
#         self.base_name = base_name
#         self.ext = ext
#         self.max_size = max_size
#         self.gzip_files = gzip_files
#         self.date = datetime.now().strftime("%Y%m%d")
#         self.run_number = self._get_next_run_number()
#         self.cycle_number = 1
#         self.current_size = 0
#         self.header = header
#         self.open_new_file()

#     def _get_next_run_number(self):
#         """Find the next available run number across all files."""
#         run_pattern = re.compile(
#             rf"{self.base_name}_(\d+)_run(\d+)_cycle\d+{self.ext}$"
#         )
#         max_run = 0
#         for fname in os.listdir("."):
#             match = run_pattern.match(fname)
#             if match:
#                 run_num = int(match.group(2))
#                 max_run = max(max_run, run_num)
#         return max_run + 1

#     def open_new_file(self):
#         if hasattr(self, "file") and self.file:
#             self._close_and_gzip()
#         self.filename = (
#             f"{self.base_name}_{self.date}_run{self.run_number}_cycle{self.cycle_number}{self.ext}"
#         )
#         self.file = open(self.filename, "w", buffering=1024*1024)
#         if self.header:
#             self.file.write(self.header + "\n") 
#             self.current_size = len(self.header) + 1
#         else:
#             self.current_size = 0
#         print(f"[INFO] Opened {self.filename}")
#         self.cycle_number += 1
#         time.sleep(1)

#     def _close_and_gzip(self):
#         """Close the current file and optionally gzip it."""
#         self.file.close()
#         if self.gzip_files:
#             gz_filename = self.filename + ".gz"
#             with open(self.filename, 'rb') as f_in, gzip.open(gz_filename, 'wb') as f_out:
#                 shutil.copyfileobj(f_in, f_out)
#             os.remove(self.filename)  # remove original uncompressed file
#             print(f"[INFO] Compressed {self.filename} -> {gz_filename}")

#     def write(self, data: str):
#         encoded = data.encode()
#         size = len(encoded)
#         if self.current_size + size > self.max_size:
#             self.open_new_file()
#         self.file.write(data)
#         self.current_size += size
#         print(self.current_size)

#     def close(self):
#         if self.file:
#             self._close_and_gzip()

class RotatingFileWriter:
    def __init__(self, base_name="output", ext=".txt", time_length = 1, gzip_files=False, header = ""):
        self.base_name = base_name
        self.ext = ext
        self.time_length = time_length
        self.gzip_files = gzip_files
        self.date = datetime.now().strftime("%Y%m%d")
        self.run_number = self._get_next_run_number()
        self.cycle_number = 1
        
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
        self.file = open(self.filename, "w", buffering = 1)#buffering=1024*1024)
        self.start_time = datetime.now()

        if self.header:
            self.file.write(self.header + "\n") 

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
        
        if datetime.now() - self.start_time >= timedelta(hours = self.time_length):
            self.open_new_file()

        self.file.write(data)
        #print(self.current_size)

    def close(self):
        if self.file:
            self._close_and_gzip()

def run_server():

    #Info Logs
    with open(connection_log, 'a') as log:
        log.write(f"\n--- Restart at {datetime.now()} ---\n")

    with open(error_log, 'a') as log:
        log.write(f"\n--- Restart at {datetime.now()} ---\n")

    with open(unique_esp_log, 'a') as log:
        log.write(f"\n--- Restart at {datetime.now()} ---\n")

    # Create the server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.setblocking(False)

    print(f"Server listening on {HOST}:{PORT}")

    sockets = [server]  # includes all connected sockets
    clients = {}        # map client socket -> {'buffer': bytearray, 'id': int}

    last_time = 0
    esp_unique_ID_list = []


    while True:

        if int(time.time())%60==0 and int(time.time())!=last_time:
            print(".")
            last_time = int(time.time())


        readable, _, _ = select.select(sockets, [], [], 0.1)

        for s in readable:
            if s is server:
                client_socket, addr = server.accept()
                time.sleep(1)
                client_socket.setblocking(False)
                sockets.append(client_socket)
                clients[client_socket] = { #Dictionary of client raw data and addresses
                    "buffer": bytearray(),
                    "addr": addr
                }
                print(f"New ESP32 connected from {addr}")
                with open(connection_log, 'a') as log:
                    log.write(f"{time.time()}: Reconnected from {addr}\n")

            else:
                client_info = clients.get(s)
                client_addr = client_info["addr"] if client_info else None
                try:
                    """peek = s.recv(4096, socket.MSG_PEEK)
                    recv_buf_size = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                    print(f"Receive buffer size: {recv_buf_size} bytes")
                    print(f"Bytes waiting in receive buffer: {len(peek)}")"""
                    data = s.recv(4096)
                    if not data:  # client closed connection gracefully
                        print(f"No data recieved from: {client_addr}")
                        with open(error_log, 'a') as f:
                            f.write(f"No data recieved from: {client_addr}")
                        if s in sockets:
                            sockets.remove(s)
                        if s in clients:
                            del clients[s]
                        s.close()

                        with open(connection_log, 'a') as log:
                            log.write(f"{time.time()}: Disconnected from {addr}\n")
                        continue
                except Exception as e: #Recieve exception
                    print(f"Error recieving data from {s}:{e}")
                    with open(error_log, 'a') as f:
                        f.write(f"[SERVER] Error recieving from {client_addr}: {e}\n")                    
                    if s in sockets:
                        sockets.remove(s)
                    if s in clients:
                        del clients[s]
                    s.close()
                    with open(connection_log, 'a') as log:
                        log.write(f"{time.time()}: Disconnected from {addr}\n")
                    continue

                

                clients[s]["buffer"].extend(data)

                # Process all complete 2-byte packets
                while len(clients[s]["buffer"]) >= PACKET_SIZE:
                    packet = clients[s]["buffer"][:PACKET_SIZE]
                    clients[s]["buffer"] = clients[s]["buffer"][PACKET_SIZE:]

                    #Unpacks data
                    inst, ID, RF, Cal, ch, w_num, ms, sub_ms, event_num, count = struct.unpack(PACKET_FORMAT, packet)
                    
                    if ID not in esp_unique_ID_list:
                        esp_unique_ID_list.append(ID)
                        with open(unique_esp_log, 'a') as f:
                            f.write(f"{str(ID)}\n")

                    if inst == 100: #Error code
                        writer.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}; {count}\n")
                        """with open(error_log, 'a') as f:
                            f.write(f"[ESP]:{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}; {count}\n") # Ignore labels; RF = Error Code"""
                        
                    elif inst == 99: #Data Code
                        if ID == 48:
                            writer.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}; {count}\n")
                            #print("BH data written to file")
                            
                            if ch == 0 and RF == 0: #Measuring time from rise                                
                                for client_sock in list(clients.keys()):
                                    if client_sock != s: #Broadcasts BH timestamp to all other clients except sender
                                        
                                        client_info = clients.get(client_sock)
                                        client_addr = client_info["addr"] if client_info else "Unknown"
                                        try:
                                            #time.sleep(0.1) #delay the broadcast by 100ms
                                            broadcast_format = '!iiiii '
                                            broadcast_packet = struct.pack(broadcast_format, inst, w_num, ms, sub_ms, event_num)
                                            broadcast = client_sock.sendall(broadcast_packet)
                                                                                                
                                            #print(f'Request for data sent:{broadcast}')
                    
                                        except Exception as e: #Broadcast exception
                                            print(f"Error sending to {client_sock}: {e}")
                                            with open(error_log, 'a') as f:
                                                f.write(f"[SERVER] Error sending to {client_addr}: {e}\n")
                                            print("Dead client sock removed:", client_sock)

                                            if client_sock in sockets:
                                                sockets.remove(client_sock)
                                            if client_sock in clients:
                                                del clients[client_sock]
                                            client_sock.close()

                                            with open(connection_log, 'a') as log:
                                                log.write(f"{time.time()}: Disconnected from {addr}\n")
                                            continue

                        else: #For other clients
                            writer.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}; {sub_ms}; {event_num}; {count}\n")
                            #print("AS data written to file   
                    else:
                        writer.write("Unknown Code\n")

                        """                        
                        with open(error_log, 'a') as f:
                            f.write("Unknown Code\n")"""
            

if __name__ == "__main__":

    try:
        while True:
            try:
                connection_log = 'connection_log.txt'
                error_log = 'error_log.txt'
                unique_esp_log = 'unique_esp_log.txt'
                HEADER = "Req Code; ID; RF; Cal; Ch, W#; t_ow mil; t_ow submil; Event"
                writer = RotatingFileWriter(base_name="gps_daq", ext=".txt", time_length = 1, header = HEADER)  # 1 MB max
                run_server()

            except Exception as e: #Auto-restart server on any errors
                print(f"[FATAL ERROR] {e}")
                traceback.print_exc()
                with open(error_log, 'a') as f:
                    f.write(f"[SERVER] Fatal error: {e}\n{traceback.format_exc()}\n")
                
                writer.close()

                print("Restarting server in 3 seconds...")
                time.sleep(3)

    except KeyboardInterrupt:
        print("DAQ Stopped")
    #Note: Im noticing the esp keeps writting to the TCP buffer even after server shutdown, becasue Im not handling closing the sockets on shutdown.
    #May be something to worry about in the future, but right now its not a concern. I can probably just have a for loop through the clients list

    finally:
        writer.close()
