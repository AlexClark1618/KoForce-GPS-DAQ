import network
import socket
import time
import random
import machine

# ---------- Wi-Fi Setup ----------
ssid = 'TP-Link_FB80'
password = 'Beau&River'

#ssid = 'ONet'
#password = ''

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
print("Connected. IP:", wlan.ifconfig()[0])

s = socket.socket()
Server_IP = '192.168.0.93'
Server_Port = 12345
s.connect((Server_IP, Server_Port))


while True:
    # First, send data to server
    try:
        message = "ESP1 says hello\n"
        s.send(message.encode())  # Make sure to encode to bytes
        print("Sent:", message.strip())
    except Exception as e:
        print("Send failed:", e)
        break

    # Then, try to receive from server
    try:
        data = s.recv(1024)
        if data:
            print("From server:", data.decode().strip())
    except OSError:
        # Timeout or no data — not an error
        pass