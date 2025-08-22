import network
import socket
import time
import select
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
'''
addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen()

poller = select.poll()

while True:

    try:
        cl, addr = s.accept()
        cl.setblocking(False)
        poller.register(cl, select.POLLIN)
        
    except OSError:
        continue

    print("Client connected:", addr)
    
    events = poller.poll(0)  # non-blocking check
    for sock, event in events:
        if event & select.POLLIN:
            data = sock.recv(1024)
            
            start = time.ticks_us()
            if data:
                end = time.ticks_us()
                print("Data received:")
                print(time.ticks_diff(end, start))
                
            else:
                # Client closed connection
                print("Client disconnected")
                poller.unregister(sock)
                sock.close()
'''
poller = select.poll()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 12345))
s.listen(5)
s.setblocking(False)
poller.register(s, select.POLLIN)

while True:
    events = poller.poll(0)
    for sock, event in events:
        if sock is s:
            try:
                cl, addr = s.accept()
                cl.setblocking(False)
                poller.register(cl, select.POLLIN)
                print("Client connected:", addr)
            except OSError:
                continue
        elif event & select.POLLIN:
            data = sock.recv(1024)
            start = time.ticks_us()
            if data:
                end = time.ticks_us()
                print("Data received:", )
                print(time.ticks_diff(end, start))

            else:
                print("Client disconnected")
                poller.unregister(sock)
                sock.close()