import socket
import time
import random as rand

HOST = '134.69.194.204'
PORT = 12345

data_file = 'data_file.txt'

with open(data_file,'w') as f:
    f.write("GET Request;Recieved Data\n")
def get_around(n, j):
    s = socket.socket()

    try:
        s.connect((HOST, PORT))
        s.send(f"GET:{n},{j}\n".encode())
        data = s.recv(1024).decode().splitlines()
        
        with open(data_file, 'a') as f:
            f.write(f'GET: {n},{j} | Recieved: {data}\n')
    
    finally:
        s.close()
        #print("Around result:", data)

while True:
    num = rand.randint(0,127)
    #print(num)
    get_around(num, 20)
    time.sleep(0.5)