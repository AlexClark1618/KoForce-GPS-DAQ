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
ssid = 'TP-Link_FB80'
password = 'Beau&River'

#ssid = 'ONet'
#password = ''
    #Have to register esp32 mac address to use ONet

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
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
count = 0

def add_to_buffer(data):
    '''
    Description - Adds integers to circular buffer

    Input - Integer
    '''
    global buffer_index, count, buffer
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
#last_read_time = time.ticks_us()

whole_loop_start = time.ticks_us()


while True:

    read_data_start = read_data_end = None
    send_data_start = send_data_end = None
    rx_buffer_start = rx_buffer_end = None
    whole_loop_end = None
    
    '''
    # Simulates adding integers to buffer at a regular interval
    if time.ticks_diff(time.ticks_us(), last_read_time) >= 1000:
        
        for i in range(max_buffer_size):
            add_to_buffer(i)
            
    last_read_time = time.ticks_us()
    '''
    
    polling_latency_start = time.ticks_us()
    events = poller.poll(1)
    polling_latency_end = time.ticks_us()

    for sock, event in events: #Loops through sockets with activity returns tuples
        if sock is s: #If socket is server socket have client connect to it
            try:
                cl, addr = s.accept()
                cl.setblocking(False)
                poller.register(cl, select.POLLIN)
                print("Client connected:", addr)
            except OSError:
                continue
        
        elif event & select.POLLIN:
            
            try:
                read_data_start = time.ticks_us()
                req = sock.recv(1024).decode().strip()
                read_data_end = time.ticks_us()

            except OSError:
                req = ""
            
            if req: #If none empty data
                
                print('Data recieved:' , req)
                
                response = '0123456789'
                    
                send_data_start = time.ticks_us()
                bytes_sent = sock.send(response.encode())
                send_data_end = time.ticks_us()

        whole_loop_end = time.ticks_us()

    if whole_loop_end is not None:
        whole_loop_elapsed = time.ticks_diff(whole_loop_end, whole_loop_start)
        print("Whole loop elapsed (us):", whole_loop_elapsed)
        whole_loop_start = time.ticks_us()  # reset for next loop

    if send_data_start is not None and send_data_end is not None:
        send_data_elapsed = time.ticks_diff(send_data_end, send_data_start)
        print("Send data time (us):", send_data_elapsed)

    if rx_buffer_start is not None and rx_buffer_end is not None:
        rx_buffer_elapsed = time.ticks_diff(rx_buffer_end, rx_buffer_start)
        print("RX buffer read time (us):", rx_buffer_elapsed)

    if read_data_start is not None and read_data_end is not None:
        read_data_elapsed = time.ticks_diff(read_data_end, read_data_start)
        print("Read data read time (us):", read_data_elapsed)
    # Optional: measure polling latency too
    polling_elapsed = time.ticks_diff(polling_latency_end, polling_latency_start)
    print("Polling latency (us):", polling_elapsed)

"""
                if req.startswith("GET:"):            
                    try:
                        _, tail = req.split(':', 1)
                        num_s, j_s = tail.split(',')
                        
                        nums = get_buffer_data(int(num_s), int(j_s))
                        
                        response = ",".join(str(x) for x in nums) + "\n"
                    except Exception as e:
                        response = "Error\n"
                        print("Error handling GET:", e)
                        
                    data = response.encode('utf-8')
                    bytes_sent = cl.send(data)
                    print("Bytes:", bytes_sent)
                    
                else:
                    cl.send(b"UNKNOWN\n")
                """

