import socket
import select
import struct

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

data_file = 'data_file.txt'

with open(data_file,'w') as f:
    f.write("Req Code; ID; RF; Cal; Ch, W#; t_ow mil; t_ow submil; Event #\n")

while True:
    readable, _, _ = select.select(sockets, [], [], 0.1)

    for s in readable:
        if s is server:
            client_socket, addr = server.accept()
            client_socket.setblocking(False)
            sockets.append(client_socket)
            clients[client_socket] = bytearray()
            print(f"New ESP32 connected from {addr}")

        else:

            try:
                peek = s.recv(2048, socket.MSG_PEEK)

                if len(peek)>0:
                    data = s.recv(1024)
                    print("data recieved")
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
                        print(event_num)
                        #Should write all BH data to borehole first. Maybe have another if below.
                        #ID == 200 for GPS test 
                        if ID == 20:
                            print(f"From BH ESP: {inst, ID, RF, Cal, ch, w_num, ms, sub_ms, event_num}")
                            with open(data_file,'a') as f:
                                f.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}, {sub_ms}; {event_num}\n")
                                print("BH data written to file")
                            if ch == 0 and RF ==0: #Signature for borehole    
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
                            
                        elif ID == 200: #For other boreholes
                            print(f'Data sent from AS')
                            with open(data_file,'a') as f:
                                f.write(f"{inst}; {ID}; {RF}; {Cal}; {ch}; {w_num}; {ms}, {sub_ms}; {event_num}\n")

                        else:
                            print('Unknown packet, cant write to file')
                    

            except (ConnectionResetError, BrokenPipeError):
                print("Client disconnected")
                sockets.remove(s)
                s.close()
                del clients[s]
