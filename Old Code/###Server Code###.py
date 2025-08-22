###Server Code###

import socket

HOST = ''  # Listen on all network interfaces
PORT = 12345  # Port to listen on (choose any free port)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f'Server listening on port {PORT}...')
    while True:
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print('Received:', data.decode())
