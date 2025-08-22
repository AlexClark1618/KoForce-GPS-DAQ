import network
import socket
import time
import select
import random
import machine
import ntptime
import ustruct

'''
Goals: 7/28/25
    Have the esp32 send data in 18byte packages. For now ill have fixed values and on the server side 
    break it up and store it in a file as ascii.
'''

# ---------- Wi-Fi Setup ----------
#ssid = 'TP-Link_FB80'
#password = 'Beau&River'

ssid = 'ONet'
password = ''
    #Have to register esp32 mac address to use ONet

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
# Get the MAC address of the station interface (STA)
mac = wlan.config('mac')  # Returns a bytes object
# Format as human-readable MAC address
mac_str = ':'.join('{:02x}'.format(b) for b in mac)
print(mac_str)

print("Connecting to Wi-Fi...")

wifi_timeout_start = time.ticks_ms()
timeout = 100000

while not wlan.isconnected():
    if time.ticks_diff(time.ticks_ms(), wifi_timeout_start) > timeout:
        print("Connecting to wifi took too long. Restarting ESP32...")
        machine.reset()
    time.sleep(0.1)
print("Connected. IP:", wlan.ifconfig()[0])

# ---------- Web Server ----------
    #Connected to server port and listens for incoming requests for data
addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1] #Listen on all networks
poller = select.poll() #Poll allows for peaking at recieve buffer
s = socket.socket()
s.setblocking(False) #Allows socket.recv to take place immediately. No waiting if there is no data to send.
s.bind(addr)
s.listen()
print('Connected to:', addr)
poller.register(s, select.POLLIN)

# ---------- Data Buffer ----------
max_buffer_size = 60
buffer = [None] * max_buffer_size
buffer_index = 0

def add_to_buffer(data):
    global buffer_index
    buffer[buffer_index] = data
    buffer_index = (buffer_index + 1) % max_buffer_size

#Data Format: (Instructions [time, etc...], GPS Ch, Rise/Fall, ESP ID, Week #, t of week milsecs, t of week submilsecs, event #)

client_sockets = set()

ntptime.settime() #Corrects ESP32 clock

last_read_time = time.time()

while True:
    # Simulate timestamp data from gps
    if (time.time() - last_read_time) >= 1: #Gets data every 1s
    
        gps_ts = (time.time()) + 946684800 # Esp32 epoch time is jan 1 2000
        add_to_buffer(gps_ts)
            
        last_read_time = time.time()
    
    events = poller.poll(0) # The rate at which it polls the rx buffer for activity

    if events:
        for sock, event in events: #Loops through sockets with activity returns tuples
            if sock is s: #If socket is server socket have client connect to it
                try:
                    #Accecpts new client
                    cl, addr = s.accept()
                    cl.setblocking(False)
                    poller.register(cl, select.POLLIN)
                    client_sockets.add(cl)
                    print("Client connected:", addr)
                except OSError:
                    print("Error accepting or registering client")
                    continue
            
            elif event & select.POLLIN: 
                try:
                    req = sock.recv(1024).decode().strip() #Reads data from rx buffer, cna change read rate
                    print(req)
                except OSError:
                    print("Error reading rx data")
                    continue
                
                if req: #If data proceed
                    
                    cmd = req.strip().split(';')

                    #print('Data recieved:' , req)
                    
                    if cmd[0] == "CMD: 1": #Processes data and collects requested integer and specified length around it                                
                        inst = int(cmd[0].replace("CMD:", "").strip())
                        ch = 1
                        RF = 0
                        ID = int(mac_str.strip().split(':')[-1]) #Last two digits of mac address
                        bh_ts = int(cmd[1].replace("T_S:", "").strip())
                        event_num = int(cmd[2].replace("Event #:", "").strip())
                        
                        coin_ts = [t for t in buffer if t is not None and (t<=(bh_ts +5) and t>=(bh_ts -5))] #5 ms time window
                        print(coin_ts)
                        packet_count = len(coin_ts) #For packet number header
                        
                        for i in range(len(coin_ts)):
                            packet = ustruct.pack('!BBBBBBIII', 
                                inst,            # char (1 byte)
                                ch,              # char (1 byte)
                                RF,              # uint8 (1 byte)
                                ID,         	 # ESP ID uint8 (1 byte)
                                i,				 #packet id (1 byte)
                                packet_count,	 #total packets (1 byte)
                                bh_ts,     		 # uint32 (4 bytes) #Q for 8 byte uint64
                                coin_ts[i],      # uint32 (4 bytes)
                                event_num        # uint32 (4 bytes)
                            )
                            #data = sock.send(packet)
                            print(f'Bytes sent: {data}')
                        
                        '''
                        test_data = [ord('T'), 1, ord('F'), 14, 1, 2, 3, 4, 5]
                        
                        #For debugging data type
                        print("FORMAT:", fmt)
                        print("DATA:", combined_data)
                        for i, d in enumerate(combined_data):
                            print(f"  [{i}] {d} -> {type(d)}")
                            
                        response = ustruct.pack('!BBBBIIIII', *test_data)
                        '''

                        
                        
                    
                    elif cmd[0] == "CMD: M":
                        packet = f'{mac_str}\n'.encode() #Converts back to bytes
                        data = sock.send(packet)
                        print(f'Bytes sent: {data}')

                    elif cmd[0] == "CMD: H":
                        packet = b'Hello\n'
                        data = sock.send(packet)
                        print(f'Bytes sent: {data}')
                        
                    else:
                        packet = b"Unknown request\n"
                        #Clear Buffer
                    
                else:
                    poller.unregister(sock)
                    client_sockets.remove(sock)
                    sock.close()