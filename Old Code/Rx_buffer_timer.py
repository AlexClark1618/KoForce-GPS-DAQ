import network
import socket
import time
import random
import machine

# ---------- Wi-Fi Setup ----------
#ssid = 'TP-Link_FB80'
#password = 'Beau&River'

ssid = 'ONet'
password = ''

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
print("Connected. IP:", wlan.ifconfig()[0])

# ---------- Web Server ----------
addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen()

# On ESP32:
cl, addr = s.accept()
print("Connection from", addr)

# Wait for some data to enter the RX buffer
time.sleep(10)

total = 0
t0 = time.ticks_us()
while True:
    data = cl.recv(1024)
    if not data:
        break
    total += len(data)
t1 = time.ticks_us()

# Report: reading speed and bytes
elapsed = time.ticks_diff(t1, t0) / 1_000_000
print(elapsed)
print(f"Bytes received: {total} , Rate: {total/elapsed/1024} kB/s")
