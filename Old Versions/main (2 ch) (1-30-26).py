#Airshower Main
#Updated- 1/28/26 

#Changelog
    #Changed logic with send and receive functions
    #New Calibration and rate calculator
    #Cleanup
    #Added null counter
    #Shrunk timewindow to 100us


import socket
import ustruct
import time
import network
from machine import UART, Pin, WDT
import time
import gc
import ota_update
import _thread
import sys

#---------OTA Function------------
try:
    with open('config.txt') as f:
        detector_num = f.read().strip()
        print("This is Detector " + detector_num)
except OSError:
    detector_num = "0"  # default if not yet set
    print("No config.txt found, using default detector number:", detector_num)

version_num = "0.09"
# wdt = None
s = None
ota_in_progress = False

def start_listener():
    global wdt, s, ota_in_progress, version_num, detector_num
    addr = socket.getaddrinfo('0.0.0.0', 8080)[0][-1]
    t = socket.socket()
    t.bind(addr)
    t.listen(1)
    print("Listening for OTA trigger on port 8080...")

    while True:
        cl, addr = t.accept()
        print('Client connected from', addr)
        request = cl.recv(1024)
        if not request:
            cl.close()
            continue

        #request = str(request)
        request = request.decode()

        if "/ota" in request:
            print("OTA trigger received")
            try:
                #wdt = WDT(1000000)  # effectively disables watchdog during OTA
                print("Watchdog disabled for OTA.")
            except Exception as e:
                print("Error disabling WDT:", e)
            
            ota_in_progress = True
            time.sleep(0.2) # check this time for timeout errors in other places
            cl.send("HTTP/1.1 200 OK\r\n\r\nUpdating...\n")
            ota_update.download_and_install(cl)
        elif "/version" in request:
            cl.send("HTTP/1.1 200 OK\r\n\r\nDetector "+ detector_num + " Firmware Version Number: " + version_num + "\n")
        else:
            cl.send(b"HTTP/1.1 200 OK\r\n\r\nHello from ESP32\n")
        cl.close()


#---------GPS Variables-----------
UBX_HDR = b'\xb5\x62' 
#RXM_TM=b'\x02\x74'
#TIM_TM2=b'\x0d\x03'
#NAV_CLOCK=b'\x01\x22'
RXM_TM =(2,116)   #b'\x02\x74'
TIM_TM2= (13,3)   #b'\x0d\x03'
NAV_CLOCK= (1,34)       #b'\x01\x22'
REQUESTED_TIME_WINDOW = 1000000  #returned times (ns) will be within +/- requested_time_window of time of interested 
# UBX poll message for NAV-CLOCK (class 0x01, ID 0x22)
POLL_NAV_CLOCK = b'\xb5\x62\x01\x22\x00\x00\x23\x6a'
uart1_tx_pin = 12  # Example: GPIO12
uart1_rx_pin = 14  # Example: GPIO14
rxbuf = (8192 * 3 ) # 24kB seems to be the max allowed within the code.
uart1 = UART(1, baudrate=115200*4, tx=Pin(uart1_tx_pin), rx=Pin(uart1_rx_pin), rxbuf=rxbuf)

time.sleep(0.1)
#NNC=10
numMeas=1
global tcoll0
tcoll0=0

# ---------- Wi-Fi Setup ----------
ssid = 'AirShower2.4G'
password = 'Air$shower24'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def clear_wifi_rx_buffer():  
    global s        
    if not s:
        print("No socket to clear.") 

    try:
        data = s.recv(1024)
     
        print("Wifi RX buffer cleared of:", len(data), "bytes")
    except Exception as e:
        print("Error during buffer clear:", e)

def con_to_wifi(ssid, password):
    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(0.1)
    
    while not wlan.isconnected():
        try:
            print("Connecting to Wi-Fi...")
            wlan.connect(ssid, password)
            time.sleep(0.1)
            while not wlan.isconnected():
                time.sleep(0.1)
            print("Wi-Fi connected.")
            return wlan.ifconfig()
        except Exception as e:
            print(f"Wifi connection attempt failed: {e}")

if con_to_wifi(ssid, password):
    _thread.start_new_thread(start_listener, ())
    print("OTA listener started in background.")           

# ---------- Wifi and Socket Variables -----------
mac_id = wlan.config('mac')[-1]  # last byte of MAC
print('mac id:', mac_id)
ip, subnet, gateway, dns = wlan.ifconfig()
ip_last_byte = int(ip.split('.')[-1])
print("ESP IP:", ip_last_byte)

HOST = '134.69.77.61' #Karbon Computer
PORT = 12345

wdt = WDT(timeout=20000) 

# ---------- Socket Functions ----------
def connect_socket(host, port):
    while True:
        try:
            s = socket.socket()
            s.connect((host, port))
            print("Socket connected.")
            return s
        except Exception as e:
            print("Failed to connect socket:", e)
            continue     

def reconnect_socket(sock):
    try:
        if sock:
            sock.close()
    except Exception as e:
        print("Error closing socket:", e)

    time.sleep(0.1)
    return connect_socket(HOST, PORT)

s = connect_socket(HOST,PORT)
#s.setblocking(False)
s.settimeout(.05) #50ms timeout

# ---------- Send and Receive Functions -----------
def send_data(d):
    global s
    try:
        return s.send(d)

    except OSError as e:
        if e.args[0] in [11, 110]:  # EAGAIN, ETIMEDOUT, (104) ECONNRESET
            print("No data to send")
            return None
        else:
            print("Send error:", e)
            error_msg = (100, mac_id, 2, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            s = reconnect_socket(s)  
            s.send(packet)
            return None

def recieve(num_bytes):
    global s
    try:
        
        return s.recv(num_bytes)
    
    except OSError as e:
        if e.args[0] in [11, 110]:  # EAGAIN, ETIMEDOUT, (104)ECONNRESET
            print("No data to receive")
            return None
        else:
            print("Receive error:", e)
            error_msg = (100, mac_id, 3, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            s = reconnect_socket(s)
            send_data(packet)
            return None

# ---------- Data Packing -----------
send_packet_format = "!iiiiiiiiii"
request_packet_format = '!iiiii'

def data_packing(packet_format: str, msg: tuple):
    try:
        packet = ustruct.pack(packet_format, 
            msg[0],#inst,            # char (1 byte)
            msg[1],#ID,
            msg[2],#RF,              # char (1 byte)
            msg[3],#cal,              # uint8 (1 byte)
            msg[4],#ch,          # uint8 (1 byte)
            msg[5],#w_num,      	 # uint32 (4 bytes) #Q for 8 byte uint64
            msg[6],#ms,         # uint32 (4 bytes)
            msg[7],#sub_ms,
            msg[8],#event_num                  # uint32 (4 bytes)
            msg[9] #count
        )
        
        return packet
    except Exception as e:
        print("Error in data packing", {e})
        #Cant send to server if error need data packing

# ---------- GPS Functions ----------
def clearRxBuf():
    print('clearRxBuf')
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    try:
        #print('clearRxBuf:', uart1.any(),'bytes')
        while uart1.any():
            print('buffer cleared of ',uart1.any(), 'bytes\n')
            (uart1.read())
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[];
        towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print("Error in clear buffer:", {e})
        error_msg = (100, mac_id, 12, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)

def maxRxBuf(n):
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    #print('maxRxBuf')
    try:
        while (uart1.any() > (n )):
            nskim = uart1.any()-n + 1000
            print('buffer cleared of ',nskim, 'bytes\n')
            (uart1.read(nskim))
            time.sleep_ms(1)
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[]; towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print('maxRxbuf exception',e)
        error_msg = (100, mac_id, 13, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)

'''
def findUBX_HDR():
    try:
        #print('findUBX_HDR')
        Byte2=0
        while Byte2 != b'\x62':
            while uart1.any() < 1:
                time.sleep_ms(0)
                pass
            Byte1 = uart1.read(1)
            while Byte1 != b'\xb5':
                #print('.',end='')
                while uart1.any() < 1:
                    time.sleep_ms(0)
                    pass
                Byte1 = uart1.read(1)
                time.sleep_ms(0)
                pass
            #print('')
            while uart1.any() < 1:
                time.sleep_ms(0)
                pass
            Byte2=uart1.read(1)
            
    except Exception:
        print("findUBX_HDR error:",e)
        error_msg = (100, mac_id, 14, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
'''

hdr = bytearray(1)
def findUBX_HDR():
    try:
        state = 0  # 0 = looking for 0xB5, 1 = looking for 0x62

        while True:
            if uart1.any() == 0:
                time.sleep_ms(1)
                continue

            uart1.readinto(hdr)  # integer, no bytes object
            b = hdr[0]
            if state == 0:
                if b == 0xB5:
                    state = 1
            else:
                if b == 0x62:
                    return  # header found
                else:
                    state = 0   
    except Exception:
        print("findUBX_HDR error:",e)
        error_msg = (100, mac_id, 14, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)


'''
def findHDR2():
    while uart1.any() < 4:
        time.sleep_ms(0)
        pass
    data0 = uart1.read(4)
    #print('Header: ',data0)
    bytehdr2 = data0[0:2]
    lenb = data0[2:4]
    leni = int.from_bytes(lenb, "little")
    return(bytehdr2, leni)
'''

hdr2 = bytearray(4)
def findHDR2():
    while uart1.any() < 4:
        time.sleep_ms(1)
    uart1.readinto(hdr2)
    cls  = hdr2[0]
    msg  = hdr2[1]
    leni = hdr2[2] | (hdr2[3] << 8)
    #print('HDR2', cls, msg, leni)
    # optional sanity check
#     if leni > 2048:
#         raise ValueError("Invalid UBX length")
    return cls, msg, leni

MAX_TOI=256

toi_RF      = [0] * MAX_TOI
toi_valid   = [0] * MAX_TOI
toi_ch      = [0] * MAX_TOI
toi_wno     = [0] * MAX_TOI
toi_Ms      = [0] * MAX_TOI
toi_SubMs   = [0] * MAX_TOI
#toi_count   = [0] * MAX_TOI

def request(wnoToi,MsToi,subMsToi):
    global slope, tcoll0, toi_len
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    try:
        #print('100')
        res=(0,0,0,0)
        if (wnoToi == -1):
          #New request
          print('request(-1,0,0) called')
          while (res[0] == 0):
              #print('res[0] ==0')
              res=readData(1)
              #print('readData(1)')
#          print('res[1]:',res[1])
          MsToi = res[1]+MsToi
          subMsToi = res[2]
          #print('end if')
        resToi=MsToi*1000000+subMsToi
#         tcoll0=time.time_ns()
#         gc.collect()
#         tcoll1=time.time_ns()
#         print('time to collect', tcoll1-tcoll0)
#        freemem=gc.mem_free()
#        print(tcoll0)
#         if (time.time_ns()-tcoll0)/1000000 > 100:
#             print('free memory:',freemem)
#             if freemem < 50000:
#                print('free memory < 50000') 
#                tcoll0=time.time_ns()
#                gc.collect()
#                tcoll1=time.time_ns()
#                print('time to collect', tcoll1-tcoll0)
#                print('free memory:', gc.mem_free())
            
        res=(0,0,0,0)
        #print("res[1]", res[1])
#        print("MsToi:", MsToi)
        #print('101')
        #print("request started")
        diff=0
#        print('free mem before readData',gc.mem_free())
        while (diff < REQUESTED_TIME_WINDOW):  # | (bytehdr2 == RXM_TM): #Exceed the time of interest by at least 1 ms and capture an extra RXM data packet    
            res=readData(1)
            #print('free mem after readData',gc.mem_free(),res[0])

#             RFRaw=RFRaw[-95:]
#             chRaw=chRaw[-95:]
#             countRaw=countRaw[-95:]
#             countCal=countCal[-2:]
#             towMsRaw=towMsRaw[-95:]
#             towMsCal=towMsCal[-2:]
#             towSubMsRaw=towSubMsRaw[-95:]
#             towSubMsCal=towSubMsCal[-2:]
            
            if res[1] > 0:
                diff=(res[1]-MsToi)*1000000+(res[2]-subMsToi)

            if res[0] != 0:
                if (abs(diff) > 1000000000) | ((res[0] != wnoToi) & (wnoToi != -1)) :
                    print('Unreasonable request', diff/1000000,'ms', res[1], MsToi)
                    error_msg = (100, mac_id, 16, diff, 0, 0, 0, 0, 0, 0)
                    packet = data_packing(send_packet_format, error_msg)
                    s.send(packet)
                    return None
#         print('102')                        
#         readData(1) #???
#         print('readData2',time.time_ns())
#         readData(1) #???
#         print('readData3',time.time_ns())
#         readData(1) #???
#         print('readData4',time.time_ns())
        timeValid = res[3]
        lastC=len(countCal)-1
        lastR=len(countRaw)-1
        #Find upper index in raw data
        #print("countRaw:", countRaw)
        #print("countCal:", countCal)
#        print("lastR:",lastR)
#        print("lastC:",lastC)
        #print("towMsRaw:",towMsRaw)
        #print("towMsCal:", towMsCal)
#        print('buffer size ',uart1.any(), 'bytes\n')
#        print('103')

#         if (lastC < 0) or (lastR < 0): #Bandaid for when there is only one calibrated data for some reason
#             print('Missing elements')
#             error_msg = (100, mac_id, 18, 0, 0, 0, 0, 0, 0, 0)
#             packet = data_packing(send_packet_format, error_msg)
#             s.send(packet)
#             return None
#        print('free mem before calib',gc.mem_free())
        for i in range(lastR,-1,-1):
            if countRaw[i]==countCal[lastC]:
                #print("i:", i)
                #print("countRaw[i]:", countRaw[i])
                #print("countCal[lastC]:", countCal[lastC])
                #print("towMsCal[lastC]:", towMsCal[lastC])
                #print("towMsRaw[i]:", towMsRaw[i])
                #print("towSubMsRaw[i]:", towSubMsRaw[i])
                #print(lastC)
                #print(towSubMsCal)
                #print("towSubMsCal[lastC]:", towSubMsCal[lastC])
                
                
                tCal1=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
                tRaw1=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
                break
#        print('104')
        #print('free mem after calib',gc.mem_free())
        
        #timesOfInterest=[]
        rfoi=[]; tvoi=[]; choi=[]; wnoi=[]; msoi=[]; submsoi=[]; countoi=[]
        toi_len=0

        for i in range(len(towMsRaw)):   #

            tRaw=towMsRaw[i]*1000000+(towSubMsRaw[i]//1000)
            res=(tRaw-tRaw1)-(tRaw-tRaw1)*slope//1000000000+tCal1
            #requested time window
            diff = res - resToi
            if diff < 0:
                diff = -diff
            if diff < REQUESTED_TIME_WINDOW:  #only keep cal data that are within 1ms of Toi.
                #print(i,'free mem',gc.mem_free(),diff)
                #res2 = divmod(res, 1000000)
                Ms=res//1000000
                SubMs = res - Ms * 1000000
                #SubMs=res2[1]
                #print(f"i:{i},resToi:{resToi},tCal1:{tCal1}, res:{res}, Ms:{Ms}, SubMs:{SubMs}")
                if (SubMs > 999999):
                    print('*************SubMs > 999999*********')
#         rfoi.append(RFRaw[i])
#         tvoi.append(timeValid)
#         choi.append(chRaw[i])
#         wnoi.append(wnoToi)
#         msoi.append(Ms)
#         submsoi.append(SubMs)
#         countoi.append(countRaw[i])
#         toi_RF      = [0] * MAX_TOI
#         toi_valid   = [0] * MAX_TOI
#         toi_ch      = [0] * MAX_TOI
#         toi_wno     = [0] * MAX_TOI
#         toi_Ms      = [0] * MAX_TOI
#         toi_SubMs   = [0] * MAX_TOI
                toi_RF[toi_len]=RFRaw[i]
                toi_valid[toi_len]=timeValid
                toi_ch[toi_len]=chRaw[i]
                toi_wno[toi_len]=wnoToi
                toi_Ms[toi_len]=Ms
                toi_SubMs[toi_len]=SubMs
                toi_len +=1
        #timesOfInterest.append((RFRaw[i],timeValid,chRaw[i],wnoToi,Ms,SubMs, countRaw[i])) 
#        print('105')
        #print('free mem end  req',gc.mem_free())

        return(toi_RF,toi_valid,toi_ch,toi_wno,toi_Ms,toi_SubMs)
    
    except Exception as e:
        print("Request error:", e)
        error_msg = (100, mac_id, 6, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        #return None

plb = bytearray(2048)
ck  = bytearray(2)
def readData(det):
    global slope
    #print('0 readData free mem:',gc.mem_free())

    try:
        # Find UBX sync
        findUBX_HDR()
        #print('1 readData free mem:',gc.mem_free())

        cls, msg, leni = findHDR2()
        if leni > 2048:
            print("leni >2048" )
            return (0, 0, 0, 0)

        # Wait cooperatively for payload + checksum
        needed = leni + 2
        while uart1.any() < needed:
            time.sleep_ms(1)

        # Read payload + checksum without allocating
        uart1.readinto(plb, leni)
        uart1.readinto(ck, 2)
        #print('2 readData free mem:',gc.mem_free())

        # ---------- RXM-TM ----------
        if (cls, msg) == RXM_TM:
            #print('RXM_TM')
            version = plb[0]
            numMeas = plb[1]

            base = 8
            for _ in range(numMeas):
                edgeInfo = (
                    plb[base+0] |
                    (plb[base+1] << 8) |
                    (plb[base+2] << 16) |
                    (plb[base+3] << 24)
                )

                RF = (edgeInfo >> 4) & 1
                ch = edgeInfo & 1

                count = plb[base+4] | (plb[base+5] << 8)
                wno   = plb[base+6] | (plb[base+7] << 8)

                towMs = (
                    plb[base+8] |
                    (plb[base+9] << 8) |
                    (plb[base+10] << 16) |
                    (plb[base+11] << 24)
                )

                towSubMs = (
                    plb[base+12] |
                    (plb[base+13] << 8) |
                    (plb[base+14] << 16) |
                    (plb[base+15] << 24)
                )

                #print('3 readData free mem:',gc.mem_free())
                #print('RX-TM',count)
                RFRaw.append(RF)
                chRaw.append(ch)
                countRaw.append(count)
                towMsRaw.append(towMs)
                towSubMsRaw.append(towSubMs)
                #print('4 readData free mem:',gc.mem_free())


                base += 24

        # ---------- TIM-TM2 ----------
        elif (cls, msg) == TIM_TM2:
            #print('5 readData free mem:',gc.mem_free())

            #print('TIM_TM2')
            ch = plb[0]
            edgeInfo = plb[1]

            edgeF     = (edgeInfo >> 2) & 1
            edgeR     = (edgeInfo >> 7) & 1
            timeValid = (edgeInfo >> 6) & 1

            count = plb[2] | (plb[3] << 8)
            wnoR  = plb[4] | (plb[5] << 8)
            wnoF  = plb[6] | (plb[7] << 8)

            towMsR = (
                plb[8] |
                (plb[9] << 8) |
                (plb[10] << 16) |
                (plb[11] << 24)
            )

            towSubMsR = (
                plb[12] |
                (plb[13] << 8) |
                (plb[14] << 16) |
                (plb[15] << 24)
            )

            towMsF = (
                plb[16] |
                (plb[17] << 8) |
                (plb[18] << 16) |
                (plb[19] << 24)
            )

            towSubMsF = (
                plb[20] |
                (plb[21] << 8) |
                (plb[22] << 16) |
                (plb[23] << 24)
            )

            accEst = (
                plb[24] |
                (plb[25] << 8) |
                (plb[26] << 16) |
                (plb[27] << 24)
            )

            if det == 1:
                #print('TIM-TM',count)

                countCal.append(count)
                towMsCal.append(towMsR)
                towSubMsCal.append(towSubMsR)
                #print('6 readData free mem:',gc.mem_free())

                return (wnoR, towMsR, towSubMsR, timeValid)

            return [
                (0, 1, ch, wnoR, towMsR, towSubMsR),
                (1, 1, ch, wnoF, towMsF, towSubMsF)
            ]

        # ---------- NAV-CLOCK ----------
        elif (cls, msg) == NAV_CLOCK:
            #print('7 readData free mem:',gc.mem_free())

            #print('NAV_CLOCK')
            iTOW = (
                plb[0] |
                (plb[1] << 8) |
                (plb[2] << 16) |
                (plb[3] << 24)
            )

            iclkBias  = ustruct.unpack_from('<i', plb, 4)[0]
            iclkDrift = ustruct.unpack_from('<i', plb, 8)[0]

            tAcc = (
                plb[12] |
                (plb[13] << 8) |
                (plb[14] << 16) |
                (plb[15] << 24)
            )

            fAcc = (
                plb[16] |
                (plb[17] << 8) |
                (plb[18] << 16) |
                (plb[19] << 24)
            )

            slope = iclkDrift
            print('** slope =', slope)
            #print('1 readData free mem:',gc.mem_free())

        # Yield once after heavy UART work
        time.sleep_ms(0)
        #print("return (0,0,0,0)")
        return (0, 0, 0, 0)

    except Exception as e:
        print("Error in readData:",e)
        error_msg = (100, mac_id, 7, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)

# ---------- Info Packets ----------
error_msg = (100, mac_id, ip_last_byte, 11, time.ticks_ms(), 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, error_msg)
send_data(packet)

time.sleep(0.1)

info_msg = (1, mac_id, ip_last_byte, 0, 0, 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, info_msg)
send_data(packet)

# ---------- Main Loop ----------
RFRaw=[]
chRaw=[]
countRaw=[]
countCal=[]
towMsRaw=[]
towMsCal=[]
towSubMsRaw=[]
towSubMsCal=[]
uart1.write(POLL_NAV_CLOCK) #Poll Nav Clock
slope=0
tRaw1=None
tCal1 = None
Valid = 0
res=None

#initialise Valid, slope  and offset 
while ((slope == 0) or (tRaw1 == None) or (Valid == 0)):
    print('\ninit while loop', slope, tRaw1, Valid, res)
    uart1.write(POLL_NAV_CLOCK) #Poll Nav Clock
    for i in range(4):
        res=readData(1)
        if (res[1] > 0):
            if (res[3] > 0):
                Valid = 1
            else:
                Valid = 0
                print("GPS not locked")
                time.sleep(1)# wait 1 second before trying again
                break
        lastC=len(countCal)-1
        lastR=len(countRaw)-1
        #print('countCal',countCal,'countRaw',countRaw)
    for i in range(lastR,-1,-1):
        #print('line 569')
        if countRaw[i]==countCal[lastC]:
            #print("i:", i)
            #print("countRaw[i]:", countRaw[i])
            #print("countCal[lastC]:", countCal[lastC])
            
            tCal1=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
            tRaw1=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
            break

null_count = 0
NEvents0 = 0
NEvents1 = 0
deltaT0 = 0
deltaT1 = 0
NEventsSent0=0
NEventsSent1=0
T0=time.ticks_us()

array_count = 0
Rate0=0
Rate1=0
R0index=[]
R1index=[]
#global toi_len

#gc.collect()
clearRxBuf()
clear_wifi_rx_buffer()

while True:
    #gc.collect()
    
    if ota_in_progress:
        print("OTA in progress: closing gps data socket")
        try:
            s.close()
            while True:
                wdt.feed()
                
        except Exception as e:
            print("Socket close error:", e)
        time.sleep(1_000_000)  # effectively idle until reset

    print("1")

    try:
        # Ensure Wi-Fi stays connected
        if not wlan.isconnected():
            print("Wi-Fi disconnected. Reconnecting...")
            con_to_wifi(ssid, password)
        
        maxRxBuf(20000)
        req = recieve(20) 
        print("2")

        if req:
            try:
                inst, w_num, ms, sub_ms, event_num = ustruct.unpack(request_packet_format, req) #There might be an error here. What if multiple messages came in at the same time and I read them all at the same time? Will they be lost as ustruct may only evaluate the first little bit?
                print("3")
            except Exception as e:
                print("Error unpacking request:", e)
                error_msg = (100, mac_id, 8, 0, 0, 0, 0, 0, 0, 0)
                packet = data_packing(send_packet_format, error_msg)
                send_data(packet)
                continue

            if inst == 99:
                RFRaw=RFRaw[-500:]
                chRaw=chRaw[-500:]
                countRaw=countRaw[-500:]
                countCal=countCal[-20:]
                towMsRaw=towMsRaw[-500:]
                towMsCal=towMsCal[-20:]
                towSubMsRaw=towSubMsRaw[-500:]
                towSubMsCal=towSubMsCal[-20:]
                
                print("Processing GPS request...")
                print('buffer size ',uart1.any(), 'bytes\n')

                timesofinterest = request(w_num, ms, sub_ms)
                print("4")
                
                if toi_len == 0 or timesofinterest is None:
                    #msg = (99, mac_id, 0, 0, 0, 0, 0, 0, event_num, array_count)
                    #packet = data_packing(send_packet_format, msg)
                    #send_data(packet)
                    print("Null")
                    null_count += 1
                    array_count+=1
                    wdt.feed()
                    pass
                
                else:
                    RF,cal,ch,w_num,ms,sub_ms = timesofinterest

                    print("7")

                    for i in range(toi_len):

                        count = array_count #timesOfInterest[i][6] #Useless replace with transit time

                        data_msg = (99, mac_id, RF[i], cal[i], ch[i], w_num[i], ms[i], sub_ms[i], event_num, count)

                        packet = data_packing(send_packet_format, data_msg)
                        print("5")
                        
                        data = send_data(packet) #Should I start checking wifi and socket are active before sending? It seems kind of pointless,
                                        #I would have to reconnect to them anyway if it I wasnt and w
                        if data:
                            array_count+=1
                            if RF==0:
                                if ch==0:
                                    NEventsSent0 +=1
                                if ch==1:
                                    NEventsSent1 +=1
                            wdt.feed()
                            print('buffer size ',uart1.any(), 'bytes\n')
                            print("data sent")
                            print("6")

                        else:
                            print("break from send data")
                            break

                R0index=[]
                R1index=[]
                #print(RFRaw)
                #print(chRaw)
                #print(towMsRaw)
                #print(len(RFRaw))
                for i in range(len(RFRaw)):
                    if RFRaw[i] == 0:
                        if chRaw[i] == 0 :
                            R0index.append(i)
                        elif chRaw[i] ==1:
                            R1index.append(i)
                #print('endfor')
                length0=len(R0index)
                length1=len(R1index)
                #print('length', length0,length1, len(towMsRaw))
                
                if length0 > 1:
                    R0indexF=R0index[0]
                    R0indexL=R0index[-1]
                    #print(R0index)
                    #print(R0indexF, R0indexL)
                    timeElapsed0=(towMsRaw[R0indexL] - towMsRaw[R0indexF])*1000000 + int((towSubMsRaw[R0indexL] - towSubMsRaw[R0indexF])/1000)
                    #print(timeElapsed0)
                    NEvents0 += length0-1
                    deltaT0 += timeElapsed0
                    #print(NEvents0,deltaT0)
                if length1 > 1:
                    R1indexF=R1index[0]
                    R1indexL=R1index[-1]
                    #print(R1index)
                    #print(R1indexF, R1indexL)
                    #print(R1indexF, R1indexL)
                    timeElapsed1=(towMsRaw[R1indexL] - towMsRaw[R1indexF])*1000000 + int((towSubMsRaw[R1indexL] - towSubMsRaw[R1indexF])/1000)
                    #print(timeElapsed1)
                    NEvents1 += length1-1
                    deltaT1 += timeElapsed1
                    #print(NEvents1,deltaT1)
                T1=time.ticks_us()
                #print('free mem after for loop2:', gc.mem_free())
            
                if time.ticks_diff(T1, T0) > 5000000:
                    #print('NEvents')
                    uart1.write(POLL_NAV_CLOCK)
                    Rate0 = round((NEvents0*1000000000)/(deltaT0+1e-9))
                    Rate1 = round((NEvents1*1000000000)/(deltaT1+1e-9))
                    RateSent0 = round(NEventsSent0*1000000/(time.ticks_diff(T1, T0))*1000)
                    RateSent1 = round(NEventsSent1*1000000/(time.ticks_diff(T1, T0))*1000)
                    print('*Rate0:',Rate0)
                    print('*Rate1:',Rate1)
                    print('*RateSent0:',RateSent0)
                    print('*RateSent1:',RateSent1)
    
                    print('***************************************************Nulls:', null_count)
                    rate_msg = (98, mac_id, Rate0, RateSent0, Rate1, RateSent1, null_count, 0, 0, 0)

                    rate_packet = data_packing(send_packet_format, rate_msg)
                    rate_data = send_data(rate_packet)

                    if rate_data: #If not none
                        NEvents0=NEvents1=NEventsSent0=NEventsSent1=deltaT0=deltaT1=0
                        T0=T1
                        null_count=0
                        wdt.feed()
                        print('buffer size ',uart1.any(), 'bytes\n')
                        print("Rate packet sent")

                    else:
                        print("Continued from rate")
                        continue  #Do not break here

        else:
            continue # Continue main loop if data not recieved

    except Exception as e:
        sys.print_exception(e)
        print("Main loop exception:", e)
        error_msg = (100, mac_id, 1, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        continue

        
        





