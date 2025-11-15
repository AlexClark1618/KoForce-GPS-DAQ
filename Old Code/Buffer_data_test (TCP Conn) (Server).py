import socket
import time
import random

#HOST = '134.69.194.204' #Oxy
HOST = '192.168.0.19' #Home
PORT = 12345


def get_around(n, j):
    s = socket.socket()
    s.connect((HOST, PORT))
    s.send(f"GET:{n},{j}\n".encode())
    data = s.recv(1024).decode().splitlines()
    s.close()
    print("Around result:", data)

while True:

    n = random.randint(0,128)
    print(n)
    get_around(n, 20)
    time.sleep(0.5)