import network
import socket
import time
import select
import random
import machine

'''
Goals: 7/17/25
    1. Start main loop based on positive peeking into recieve buffer
    2. Test timing of sending 10 bytes and other small sections of code
    3. Use machine library to have esp32 automatically restart if some major error occurs

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
addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1] 
poller = select.poll() #Poll allows for peaking at recieve buffer
s = socket.socket()
s.setblocking(False) #Allows socket.recv to take place immediately. No waiting if there is no data to send.
s.bind(addr)
s.listen()
print('Connected to:', addr)
poller.register(s, select.POLLIN)

# ---------- Recieve Buffer ---------

    
# ---------- Data Buffer ----------
max_buffer_size = 128
buffer = [None] * max_buffer_size
buffer_index = 0

def add_to_buffer(data):
    '''
    Description - Adds integers to circular buffer

    Input - Integer
    '''
    global buffer_index, buffer
    buffer[buffer_index] = data
    buffer_index = (buffer_index + 1) % max_buffer_size
    
def get_buffer_data(num_from_server, j: "Length you want to collect"):
    '''
    Description- Once recieving the number/ timestamp from the server, this function will find the matching element 
    in the circular buffer and return all integers around it to a specified length

    Inputs (num_from_server; j)- Integers

    Output - List
    '''
    # Find the first matching index
    try:
        idx = buffer.index(num_from_server)
    except ValueError:
        return []
    # Return slice around the index, handling wrap-around
    result = []
    for offset in range(-j, j+1):
        i = (idx + offset) % max_buffer_size
        result.append(buffer[i])
    return result

# ---------- Main Loop ----------
last_read_time = time.ticks_us()

client_sockets = set()

while True:
    
    # Simulates adding integers to buffer at a regular interval
    if time.ticks_diff(time.ticks_us(), last_read_time) >= 1000:
        for i in range(max_buffer_size):
            add_to_buffer(i)
            
    last_read_time = time.ticks_us()
    

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
                except OSError:
                    print("Error reading rx data")
                    continue
                
                if req: #If data proceed
                    
                    #print('Data recieved:' , req)

                    if req.startswith("GET:"): #Processes data and collects requested integer and specified length around it        
                        try:
                            _, tail = req.split(':', 1)
                            num_s, j_s = tail.split(',')
                            
                            nums = get_buffer_data(int(num_s), int(j_s))
                            
                            response = ",".join(str(x) for x in nums) + "\n"
                        except Exception as e:
                            response = "Error\n"
                            print("Error handling GET:", e)
                            
                        data = response.encode('utf-8')
                        bytes_sent = sock.send(data)
                        print("Bytes:", bytes_sent)
                        
                    else:
                        sock.send(b"Unknown request\n")
                        
                else:
                    poller.unregister(sock)
                    client_sockets.remove(sock)
                    sock.close()
                    

