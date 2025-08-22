import socket
import ustruct
import time
import network
import select

# ---------- Functions ----------
def con_to_wifi(ssid, password):
    if wlan.isconnected(): #If somehow wifi is still connected, skip
        print("Already connected to Wi-Fi.")
        return

    print("Connecting to Wi-Fi...") #Else try connecting to wifi

    try:
        wlan.disconnect()  # Ensure clean state
        time.sleep(1)      # Let the interface settle
    except Exception as e:
        print("Disconnect error (ignorable):", e)

    try:
        wlan.connect(ssid, password)
        timeout = 10  # seconds
        while not wlan.isconnected() and timeout > 0: #Not actually a time out. Just for visual feed back that it is trying to connect.
            print("Waiting for connection...")
            time.sleep(1)
            timeout -= 1

        if wlan.isconnected():
            print("Wi-Fi connected.")
        else:
            print("Failed to connect to Wi-Fi.")

    except OSError as e:
        print("Wi-Fi connection error:", e)

packet_format = "!IIIIIIIII"

def data_packing(packet_format: str):
    packet = ustruct.pack(packet_format, 
        inst,            # char (1 byte)
        ID,
        RF,              # char (1 byte)
        cal,              # uint8 (1 byte)
        ch,          # uint8 (1 byte)
        w_num,      	 # uint32 (4 bytes) #Q for 8 byte uint64
        ms,         # uint32 (4 bytes)
        sub_ms,
        event_num                  # uint32 (4 bytes)
    )
    
    return packet

def connect_socket(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        print("Socket connected.")
        return s
    except OSError as e:
        print("Failed to connect socket:", e)
        return None
    
def clear_rx_buffer(sock, poller):
    while True:
        events = poller.poll(0)  # timeout = 0 means don't wait
        if not events:
            print('rx buffer cleared')
            break
        try:
            sock.recv(1024)
        except OSError:
            break

# ---------- Wi-Fi Setup ----------
ssid = 'TP-Link_FB80'
password = 'Beau&River'

#ssid = 'ONet'
#password = ''

#These can be moved to the main wifi function, but I thinks its more versitile to define them as globals
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

con_to_wifi(ssid, password)
mac_id = wlan.config('mac')[-1]  # last byte of MAC
print('mac_id:',mac_id)

# ---------- Connecting to Server ----------
HOST = '192.168.0.93'
#HOST = '134.69.200.155'
PORT = 12345

s = connect_socket(HOST,PORT)

# ---------- For peeking ----------
poller = select.poll()
poller.register(s, select.POLLIN)

# ---------- Main Loop ----------
clear_rx_buffer(s, poller)
event_num = 0 #Keeps track of borehole events (could be moved to server)
while True:
    #Checks for wifi disconnections. (May want to move this to an exception handle)
    if not wlan.isconnected():
        print("Wi-Fi lost. Reconnecting...")
        con_to_wifi(ssid, password)
        #After connecting to wifi its best to restablish the socket
        try:
            poller.unregister(s)
            s.close()
        except:
            pass
        
        time.sleep(1)
        s = connect_socket(HOST, PORT)
        if s:
            poller.register(s, select.POLLIN)
            continue
    
    events = poller.poll(0) 
    
    inst = 0            
    ID = mac_id
    RF = 0               
    cal = 0             
    ch = 0         
    w_num = int(time.time())  
    ms = int(time.time())      
    sub_ms = int(time.time())
    
    try:
        packet = data_packing(packet_format)

        data = s.send(packet)
        print(f'Bytes sent: {data}') #Prints byte size
    
    #Attempts to handle socket disconnecting. Reconnects and then resumes sending data.
    except OSError as e: 
        print("Socket error:", e)
        try:
            poller.unregister(s)
            s.close()
        except:
            pass
        
        time.sleep(1)
        s = connect_socket(HOST, PORT)
        if s:
            poller.register(s, select.POLLIN)
            continue

    event_num +=1
    
    time.sleep(1)
    
    if events:
        req = s.recv(1024)
        print("You got data!")

    

