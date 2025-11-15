import socket
import time

HOST = '192.168.0.19'  # Replace with your ESP32 IP
PORT = 12345

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)  # 10 seconds timeout for socket operations
s.connect((HOST, PORT))

print("Connected to ESP32. Starting idle test...")

start_time = time.time()

try:
    while True:
        # Don't send or receive data, just check connection status
        time.sleep(1)
        # Try to send a small zero-byte to detect disconnect (won't actually send)
        s.send(b'')
except Exception as e:
    elapsed = time.time() - start_time
    print(f"Connection closed after {elapsed:.2f} seconds: {e}")

s.close()


