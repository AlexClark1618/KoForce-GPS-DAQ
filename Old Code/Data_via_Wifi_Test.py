###For Connecting to Wifi###
'''
import network

#Info

# Create a station interface
sta_if = network.WLAN(network.STA_IF)

# Activate the interface
sta_if.active(True)

# Connect to your Wi-Fi network (SSID, Password)
#sta_if.connect('ONet', '')
sta_if.connect('TP-Link_FB80', 'Beau&River')


# Wait for connection
import time
for _ in range(20):
    if sta_if.isconnected():
        break
    print('Waiting for connection...')
    time.sleep(1)
    
if sta_if.isconnected():
    print('Connected to Wi-Fi')
    print('Network config:', sta_if.ifconfig())
else:
    print('Not connected')
'''

import socket
import time

HOST = '134.69.194.204' #Home
#HOST = '134.69.194.204' #Oxy
PORT = 12345

message = b'0123456789' # exactly 10 bytes

addr = socket.getaddrinfo(HOST, PORT)[0][-1]
s = socket.socket()
s.connect(addr)

while True:
    s.send(message)
    time.sleep(0.1)  # Send bytes over TCP
    
    """data = s.recv(1024).decode().strip()
    print(data)"""
#Try sending binary data later

'''
my_latitude = 34.15072
my_longitute = -118.3707367

raw_data = ustruct.pack('dd', my_latitude, my_longitute) #dd for 64 bit float
data_prefix = ustruct.pack('H', len(raw_data))

data = data_prefix + raw_data

#Lets try with json
gps_data = {
    "latitude":34.15072,
    "longitude":-118.3707367,
    "timestamp": utime.time()
}

json_bytes = ujson.dumps(gps_data).encode('utf-8')


addr = socket.getaddrinfo(HOST, PORT)[0][-1]
s = socket.socket()
s.connect(addr)
s.send(json_bytes)  # Send bytes over TCP
s.close()


def send_data(message_bytes):
    addr = socket.getaddrinfo(HOST, PORT)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(message_bytes)
    s.close()

while True:
    send_data(message_bytes)
    print('Encoded data sent')
    time.sleep(5)
'''
