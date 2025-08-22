import network
import socket
import time

ssid = 'TP-Link_FB80'
password = 'Beau&River'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
print("Connected. IP:", wlan.ifconfig()[0])

addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1] #Listening on port 12345
s = socket.socket()
s.bind(addr)
s.listen(1)

cl, addr = s.accept()
print("Connection from", addr)


try:
    while True:
        # Do NOT send or receive any data
        time.sleep(1)
except Exception as e:
    print("Connection closed:", e)

cl.close()
s.close()
