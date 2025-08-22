import socket, time

HOST = '134.69.194.204'
PORT = 12345

# Create a large payload — e.g. 50 KB
payload = b"A" * 1024 * 1000

s = socket.socket()
s.connect((HOST, PORT))

#while True:

print(f"Sending {len(payload)} KB to ESP32…")
#t0 = time.time_ns()
s.sendall(payload)
time.sleep(0.1)
#print(f"Sent in {((time.time_ns() - t0)/1000000000):.4f} seconds")
