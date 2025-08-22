#Updated: 8/4/24

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
 
send_packet_format = "!IIIIIIIII"
broadcast_packet_format = '!IIIII'

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
print('mac_id:', mac_id)
# ---------- Connecting to Server ----------
HOST = '192.168.0.93'
#HOST = '134.69.200.155'
PORT = 12345

time.sleep(1)
s = connect_socket(HOST,PORT)

# ---------- For peeking ----------
poller = select.poll()
poller.register(s, select.POLLIN)

# ---------- Main Loop ----------
clear_rx_buffer(s, poller)
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
    
    events_in = poller.poll(1) #Checks for socket activity    
    
    if events_in: #If activity proceed
        try:
            print('Data recieved')
            req = s.recv(1024) #Request from server
            print(req)
        except OSError as e:
            print("recv() error:", e)
            continue #Return to the top of the loop
                    
        
        if req: #If request proceed
            try:
                inst, w_num, ms, sub_ms, event_num = ustruct.unpack(broadcast_packet_format, req) #unpack data

            except:
                print("Error unpacking")
   
            inst = 0            
            ID = 1
            RF = 0               
            cal = 0             
            ch = 0         
            w_num = int(time.time())  
            ms = int(time.time())      
            sub_ms = int(time.time())
            
            if wlan.isconnected(): #Checks wifi is still connected before sending data
                poller.modify(s, select.POLLOUT)
                events_out = poller.poll(1) 
                
                if events_out and events_out[0][1] & select.POLLOUT: #Checks socket is ready to be written to before sending data
                    try:
                        for i in range(30): #Just practice to send 30 packets at a time
                            packet = data_packing(send_packet_format)
                            
                            data = s.send(packet)
                            print(f'Bytes sent: {data}') #Prints byte size

                    except OSError as e: 
                        print("Error sending data:", e)
                        try: #Reregister socket
                            poller.unregister(s)
                            s.close()
                        except:
                            pass
                        
                        time.sleep(1)
                        s = connect_socket(HOST, PORT)
                        if s:
                            poller.register(s, select.POLLIN)
                            continue
                else:
                    print("Socket not ready for writing")
                    continue
            else:
                print("Cannot send becauce wifi lost connection. Reconnecting now...")
                wlan.disconnect() #Makes sure its in the right state and returns to beginning of loop to reconnect wifi and socket
                continue







