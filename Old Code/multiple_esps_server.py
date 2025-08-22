import socket, select, time

HOST, PORT = '0.0.0.0', 12345
server = socket.socket()
server.bind((HOST, PORT))
server.listen()
server.setblocking(False)

clients = []

print("Server listening on port", PORT)

def broadcast(message_bytes):
    for client in clients[:]:
        try:
            client.sendall(message_bytes)
        except Exception as e:
            print("Removing disconnected client:", e)
            clients.remove(client)
            client.close()

while True:
    # Use select to find new connections or data from existing clients
    rlist, _, _ = select.select([server] + clients, [], [], 0.1)
    for s in rlist:
        if s is server:
            conn, addr = server.accept()
            conn.setblocking(False)
            clients.append(conn)
            print("Client connected:", addr)
            print(clients)

        else:
            data = s.recv(1024)
            if not data:
                print("Client disconnected")
                clients.remove(s)
                s.close()
            else:
                print("Received from client:", data)

    # Example: broadcast a heartbeat every second
    # You can adapt this loop to use threading or async as needed
    broadcast_data = b"Hello from your master\n"
    if clients:
        broadcast(broadcast_data)
        #print(clients)
    time.sleep(1)
