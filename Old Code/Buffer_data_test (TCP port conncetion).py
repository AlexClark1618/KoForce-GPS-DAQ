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

# ---------- Web Server ----------
addr = socket.getaddrinfo("0.0.0.0", 12345)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen()

# ---------- Recieve Buffer ---------
max_r_buffer_size = 1
r_buffer = [None] * max_r_buffer_size
r_buffer_index = 0

def add_to_r_buffer(data):
    global r_buffer_index, r_count, r_buffer
    r_buffer[r_buffer_index] = data
    r_buffer_index = (r_buffer_index + 1) % max_r_buffer_size
    
# ---------- Data Buffer ----------
max_buffer_size = 128
buffer = [None] * max_buffer_size
buffer_index = 0
count = 0

def add_to_buffer(data):
    global buffer_index, count, buffer
    buffer[buffer_index] = data
    buffer_index = (buffer_index + 1) % max_buffer_size
    
def get_buffer_data(num_from_server, j: "Length you want to collect"):
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

while True:
    # Simulate reading sensor every 5 seconds
    if time.ticks_diff(time.ticks_us(), last_read_time) >= 1000:
        
        for i in range(max_buffer_size):
            add_to_buffer(i)
            
    last_read_time = time.ticks_us()

    try:
        cl, addr = s.accept()
    except OSError:
        continue

    print("Client connected:", addr)
    cl.settimeout(1.0)
    
    #Prints request from server
    try:
        req = cl.recv(64).decode().strip()
        test_time_start = time.ticks_us()

    except OSError:
        req = ""
        
    print("Request:", req)

    if req.startswith("GET:"):
                
        try:
            _, tail = req.split(':', 1)
            num_s, j_s = tail.split(',')
            add_to_r_buffer(num_s)
            
            r_test_time_start = time.ticks_us()
            r_num = r_buffer[-1]
            r_test_time_end = time.ticks_us()
            
            nums = get_buffer_data(int(r_num), int(j_s))
            
            response = ",".join(str(x) for x in nums) + "\n"
        except Exception as e:
            response = "Error\n"
            print("Error handling GET:", e)
            
        data = response.encode('utf-8')
        bytes_sent = cl.send(data)
        print("Bytes:", bytes_sent)
        test_time_end = time.ticks_us()
        
    else:
        cl.send(b"UNKNOWN\n")

    cl.close()
    print("Connection closed.")
    print("Time to read from buffer and send:" , time.ticks_diff(test_time_end, test_time_start))
    print("Time to read from r_buffer:", time.ticks_diff(r_test_time_end, r_test_time_start))
    print(r_buffer)
