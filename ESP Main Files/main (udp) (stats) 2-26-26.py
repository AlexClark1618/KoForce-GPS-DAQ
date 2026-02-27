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
import select
from machine import freq

from PPS import init_time, pps_irq, ubx_checksum, ubx_send, ubx_recv, poll_gps_time, discipline_rtc,rtc_to_gps_wno_ms_subms


freq(240000000)

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
t = None
ota_in_progress = False

def start_listener():
    global wdt, t, ota_in_progress, version_num, detector_num
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
#ssid = 'TP-Link_7A54'
#password = '38694424'
ssid = 'AirShower2.4G'
password = 'Air$shower24'
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm=network.WLAN.PM_NONE)

wlan.config(pm = 0)


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
                time.sleep(0.5)
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
            time.sleep(1)
            print("Socket connected.")
            return s
        except Exception as e:
            print("Failed to connect socket:", e)
            time.sleep(1)
            continue     

"""def reconnect_socket(sock):
    try:
        if sock:
            sock.close()
    except Exception as e:
        print("Error closing socket:", e)

    time.sleep(0.1)
    return connect_socket(HOST, PORT)"""

s = connect_socket(HOST,PORT)
#s.setblocking(False)
s.settimeout(.05) #50ms timeout

poller = select.poll()
poller.register(s, select.POLLIN)

def reconnect_socket(sock, poller):
    try:
        poller.unregister(sock)
    except:
        pass

    try:
        sock.close()
    except:
        pass

    time.sleep_ms(100)

    s = connect_socket(HOST, PORT)

    poller.register(s, select.POLLIN)
    return s

# ---------- Send and Receive Functions -----------
def send_data(d):
    global s
    try:
        return s.send(d)

    except OSError as e:
        if e.args[0] in [11, 110]:  # EAGAIN, ETIMEDOUT, ECONNRESET
            print("No data to send")
            return None
        else:
            print("Send error:", e)
            error_msg = (100, mac_id, 2, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            s.send(packet)
            s = reconnect_socket(s, poller)  
            return None

def receive(num_bytes, timeout):
    global s
    events = poller.poll(timeout)
    if not events:
        #time.sleep_ms(1)
        return None
    
    try:
        return s.recv(num_bytes)
    
    except Exception as e:
        print("Receive error:", e)
        error_msg = (100, mac_id, 3, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        s = reconnect_socket(s, poller)  
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
            nskim = uart1.any()-n + 2000
            print('buffer cleared of ',nskim, 'bytes\n')
            (uart1.read(nskim))
            #time.sleep_ms(1)
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[]; towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print('maxRxbuf exception',e)
        error_msg = (100, mac_id, 13, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)

hdr = bytearray(1)
def findUBX_HDR():
    try:
        state = 0  # 0 = looking for 0xB5, 1 = looking for 0x62

        while True:
            if uart1.any() == 0:
                #time.sleep_ms(1)
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

hdr2 = bytearray(4)
def findHDR2():
    while uart1.any() < 4:
        time.sleep_ms(0)
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
    T_r_s = time.ticks_us()

    global slope, tcoll0, toi_len, unreas_count
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

            
        res=(0,0,0,0)

        diff=0
#        print('free mem before readData',gc.mem_free())
        res=readData(1)        
#      print('free mem before readData',gc.mem_free())
        while res[1] == 0:
            #print(res)
            res=readData(1)
            #continue
         
        diff=(res[1]-MsToi)*1000000+(res[2]-subMsToi)

        #print("diff", diff)
        # request is later than now or if request is sooner than start of additional buffer the U.Req.
        #print(rtc_to_gps_wno_ms_subms())
        #print(res)
        wno, Ms, subMs = rtc_to_gps_wno_ms_subms()
        
        if ((MsToi > Ms) or (MsToi < towMsCal[0])) or ((res[0] != wnoToi) and (wnoToi != -1)):
        #if ((diff > REQUESTED_TIME_WINDOW) or (diff < -1000000000))  or ((res[0] != wnoToi) and (wnoToi != -1)):
            print('##################################Unreasonable request', towMsCal[0], Ms, MsToi)
        #if ((diff > REQUESTED_TIME_WINDOW) or (diff < -1000000000))  or ((res[0] != wnoToi) and (wnoToi != -1)):
            #print('##################################Unreasonable request', diff//1000000,'ms', res[1], MsToi)
            unreas_count += 1
            ur_msg = (93, mac_id, towMsCal[0], MsToi, gc.mem_free(), buf_size, trans_time, req_diff, event_num, 0) ###
            print(ur_msg)
            send_packet = data_packing(send_packet_format, ur_msg) ###
            send_data(send_packet) 
        
        while (diff < REQUESTED_TIME_WINDOW):  # | (bytehdr2 == RXM_TM): #Exceed the time of interest by at least 1 ms and capture an extra RXM data packet    
            res=readData(1)

            if res[1] > 0:
                diff=(res[1]-MsToi)*1000000+(res[2]-subMsToi)
            
            '''
            if res[0] != 0:
                if (diff > REQUESTED_TIME_WINDOW) or (abs(diff) > 1000000000) or ((res[0] != wnoToi) and (wnoToi != -1)) :
                    print('##################################Unreasonable request', diff//1000000,'ms', res[1], MsToi)
                    unreas_count += 1
                    print(unreas_count)
            '''

        timeValid = res[3]
        lastC=len(countCal)-1
        lastR=len(countRaw)-1


        for i in range(lastR,-1,-1):
            if countRaw[i]==countCal[lastC]:

                
                
                tCal1=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
                tRaw1=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
                break

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

                toi_RF[toi_len]=RFRaw[i]
                toi_valid[toi_len]=timeValid
                toi_ch[toi_len]=chRaw[i]
                toi_wno[toi_len]=wnoToi
                toi_Ms[toi_len]=Ms
                toi_SubMs[toi_len]=SubMs
                toi_len +=1
        T_r_e = time.ticks_us()
        print("Req Time:", time.ticks_diff(T_r_e, T_r_s))
        return(toi_RF,toi_valid,toi_ch,toi_wno,toi_Ms,toi_SubMs)
    
    except Exception as e:
        sys.print_exception(e)

        print("Request error:", e)
        error_msg = (100, mac_id, 6, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        #return None

plb = bytearray(2048)
ck  = bytearray(2)
NEvents0 = 0
NEvents1 = 0
#deltaT0 = 0
#deltaT1 = 0
deltaT = 0

def readData(det):
    T_rd_s = time.ticks_us()
    
    global slope, deltaT, NEvents0, NEvents1
    global RFRaw, chRaw, countRaw
    global countCal, towMsRaw, towMsCal
    global towSubMsRaw, towSubMsCal
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
            time.sleep_ms(0)
            

        # Read payload + checksum without allocating
        uart1.readinto(plb, leni)
        uart1.readinto(ck, 2)
        #print('2 readData free mem:',gc.mem_free())

        # ---------- RXM-TM ----------
        if (cls, msg) == RXM_TM:
            #print('RXM_TM')
            version = plb[0]
            numMeas = plb[1]
            
            deltaT += 50            

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
                #print(gc.mem_free())
                #print(len(towMsRaw))
                towMsRaw.append(towMs)
                towSubMsRaw.append(towSubMs)
                #print('4 readData free mem:',gc.mem_free())
                if RF==0:
                    if ch==0:
                        NEvents0 +=1
                    elif ch==1:
                        NEvents1 +=1

                base += 24
            T_rd_e = time.ticks_us()
            #print("RD Time:", time.ticks_diff(T_rd_e, T_rd_s))
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
            T_rd_e = time.ticks_us()
            print("RD Time:", time.ticks_diff(T_rd_e, T_rd_s))
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
        sys.print_exception(e)
        RFRaw=[]
        chRaw=[]
        countRaw=[]
        countCal=[]
        towMsRaw=[]
        towMsCal=[]
        towSubMsRaw=[]
        towSubMsCal=[]
        print("Error in readData:",e)
        error_msg = (100, mac_id, 7, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)

# ---------- Info Packets ----------
error_msg = (100, mac_id, ip_last_byte, 11, time.ticks_ms(), 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, error_msg)
send_data(packet)

time.sleep(0.1)

info_msg = (1, mac_id, ip_last_byte, int(detector_num), 0, 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, info_msg)
send_data(packet)

# ---------- Main Loop ----------

global RFRaw, chRaw, countRaw
global countCal, towMsRaw, towMsCal
global towSubMsRaw, towSubMsCal
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
prev_cal = 0

#initialise Valid, slope  and offset 
while ((slope == 0) or (tRaw1 == None) or (Valid == 0)):
    print('\ninit while loop', slope, tRaw1, Valid, res)
    uart1.write(POLL_NAV_CLOCK) #Poll Nav Clock
    for i in range(4):
        res=readData(1)
        time.sleep_ms(0)
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
NEventsSent0=0
NEventsSent1=0
NEventsSentBoth = 0
T0=time.ticks_us()

array_count = 0
Rate0=0
Rate1=0
R0index=[]
R1index=[]
global toi_len

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("0.0.0.0", 12346))
#udp_sock.setblocking(False)#gc.collect()
udp_sock.settimeout(0.01)
for i in range(5):
    clearRxBuf()
    clear_wifi_rx_buffer()
    time.sleep(0.1)

send_buffer = bytearray()
#receive_buffer = bytearray()
rate_send_buffer = bytearray()



buf_size = 0
unreas_count = 0
ch0_null_count= 0
ch1_null_count= 0

init_time(uart1)

request_bunching = []
transit_time_list= []
loop_time = []
proc_time = []
rx_count = 0
prev_req = 0

while True:
    #gc.collect()
    receive_buffer = bytearray()
    T_loop_s = time.ticks_us()
    if ota_in_progress:
        print("OTA in progress: closing gps data socket")
        try:
            t.close()
            while True:
                wdt.feed()
                
        except Exception as e:
            print("Socket close error:", e)
        time.sleep(1_000_000)  # effectively idle until reset

    #print("1")

    try:
        # Ensure Wi-Fi stays connected
        if not wlan.isconnected():
            print("Wi-Fi disconnected. Reconnecting...")
            con_to_wifi(ssid, password)
        buf_size = uart1.any()
        if uart1.any()>24000:
            print("Buffer Overload")
            error_msg = (100, mac_id, 16, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            send_data(packet)
            
        maxRxBuf(20000)
        #print('buffer size ',uart1.any(), 'bytes\n')
        #req = receive(1024, 10)
        try:
            data, addr = udp_sock.recvfrom(1024)
        except Exception:
    # No data received in 10 ms
            continue
        time.sleep_ms(0)
        #print("2")
       
        if data:
            wdt.feed()

            
            receive_buffer += data
            print('len of rx buf', len(receive_buffer))
            req_bunch = len(receive_buffer)//20
            request_bunching.append(req_bunch)
            
        while len(receive_buffer)>0:
            rx_count +=1
            req = receive_buffer[:20]
            receive_buffer = receive_buffer[20:]
            
            #print("Rx:", len(req))
            ch0_flag = 0
            ch1_flag = 0
            ch0_data_flag = 0
            ch1_data_flag = 0
            
            timeStamp=rtc_to_gps_wno_ms_subms()
            print(timeStamp)
            
            try:
                inst, w_num, ms, sub_ms, event_num = ustruct.unpack(request_packet_format, req) #There might be an error here. What if multiple messages came in at the same time and I read them all at the same time? Will they be lost as ustruct may only evaluate the first little bit?
                #print(event_num)
                trans_time = timeStamp[1] - ms
                req_diff = ms -prev_req
                prev_req = ms
                #print(trans_time)
                transit_time_list.append(trans_time)
               
                print("3")
            except Exception as e:
                sys.print_exception(e)
                print("Error unpacking request:", e)
                error_msg = (100, mac_id, 8, 0, 0, 0, 0, 0, 0, 0)
                packet = data_packing(send_packet_format, error_msg)
                send_data(packet)
                continue

            if inst == 99:
                RFRaw=RFRaw[-250:]
                chRaw=chRaw[-250:]
                countRaw=countRaw[-250:]
                countCal=countCal[-20:]
                towMsRaw=towMsRaw[-250:]
                towMsCal=towMsCal[-20:]
                towSubMsRaw=towSubMsRaw[-250:]
                towSubMsCal=towSubMsCal[-20:]
                
                print("Processing GPS request...")
                print('buffer size ',uart1.any(), 'bytes\n')
                
                T_req_s = time.ticks_us()
                timesofinterest= request(w_num, ms, sub_ms)
                T_req_e = time.ticks_us()
                proc_time.append(time.ticks_diff(T_req_e, T_req_s))
                #print("Proc time:", time.ticks_diff(T_req_e, T_req_s))
                print("4")
                
                #print("toi", timesofinterest)
                #print("toi_len", toi_len)                    
                
                if toi_len == 0 or timesofinterest is None:
                    #print("Null")
                    null_count += 1
                    
                    '''
                    if ch0_flag == 0 and ch1_flag == 0:
                        
                        ch0_null_msg = (99, mac_id, 0, 0, 0, 0, 0, 0, event_num, buf_size)
                        send_packet_0 = data_packing(send_packet_format, ch0_null_msg)
                        send_buffer+= send_packet_0
                        ch1_null_msg = (99, mac_id, 0, 0, 1, 0, 0, 0, event_num, buf_size)
                        send_packet_1 = data_packing(send_packet_format, ch1_null_msg)
                        send_buffer+= send_packet_1
                    
                        send_data(send_buffer)
                    '''
                    #send_buffer = bytearray()
                    pass
                
                else:
                    RF,cal,ch,w_num,ms,sub_ms = timesofinterest

                    print("7")

                    for i in range(toi_len):

                        data_msg = (99, mac_id, RF[i], cal[i], ch[i], w_num[i], ms[i], sub_ms[i], event_num, buf_size)

                        send_packet = data_packing(send_packet_format, data_msg)
                        print("5")
                        
                        send_buffer+= send_packet
                        #print('length send buf:', len(send_buffer))
                        if RF[i]==0 and ch[i]==0:
                            NEventsSent0 +=1
                            ch0_data_flag = 1
                        if RF[i]==0 and ch[i]==1:
                            NEventsSent1 +=1
                            ch1_data_flag = 1

                                
                        if ch[i]==0 and ch0_flag == 0:
                            #print('ch0_event')
                            ch0_flag = 1
                                
                        if ch[i]==1 and ch1_flag == 0:
                            #print('ch1_event')
                            ch1_flag = 1

                        #print('buffer size ',uart1.any(), 'bytes\n')
                        print("6")
                    
                    if ch0_flag == 0:
                        ch0_null_count += 1
                        #data_msg = (99, mac_id, 0, 0, 0, 0, 0, 0, event_num, buf_size)
                        #send_packet = data_packing(send_packet_format, data_msg)
                        #send_buffer+= send_packet

                    if ch1_flag == 0:
                        ch1_null_count += 1
                        #data_msg = (99, mac_id, 0, 0, 1, 0, 0, 0, event_num, buf_size)
                        #send_packet = data_packing(send_packet_format, data_msg)
                        #send_buffer+= send_packet
                    
                    if ch0_data_flag == 1 and ch1_data_flag == 1:
                        NEventsSentBoth += 1


                    data = send_data(send_buffer) #Should I start checking wifi and socket are active before sending? It seems kind of pointless,
                    if data: 
                        print("!!!!!!!!!!!!!!!!!!!!!data sent", len(send_buffer) )
                    send_buffer = bytearray()
                
            
                T1=time.ticks_us()
                #print('free mem after for loop2:', gc.mem_free())
            
                if time.ticks_diff(T1, T0) > 5000000:
                    
                    '''
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
                    rate_msg = (98, mac_id, Rate0, RateSent0, Rate1, RateSent1, null_count, unreas_count, 0, 0)

                    rate_packet = data_packing(send_packet_format, rate_msg)
                    rate_data = send_data(rate_packet)
                    '''
                    print('NEvents')
                    uart1.write(POLL_NAV_CLOCK)
                    wno, Ms, subMs = rtc_to_gps_wno_ms_subms()
                                        
                    rate_msg1 = (98, mac_id, NEvents0, NEvents1, deltaT, wno, Ms, subMs, ch0_null_count, ch1_null_count)
                    rate_packet1 = data_packing(send_packet_format, rate_msg1)
                    rate_send_buffer+= rate_packet1

                    rate_msg2 = (95, mac_id, null_count, unreas_count, 0, 0, 0, 0, 0, 0)
                    rate_packet2 = data_packing(send_packet_format, rate_msg2)
                    rate_send_buffer+= rate_packet2

                    statsmsg1 = (96, mac_id, sum(proc_time) // len(proc_time), max(proc_time), sum(loop_time) // len(loop_time), max(loop_time), 0, 0, 0, 0)
                    statspacket1 = data_packing(send_packet_format, statsmsg1)
                    rate_send_buffer+= statspacket1

                    statmsg2 = (97, mac_id, sum(transit_time_list) // len(transit_time_list), min(transit_time_list), max(transit_time_list), sum(request_bunching) // len(request_bunching), max(request_bunching), unreas_count, rx_count, 0)
                    statspacket2 = data_packing(send_packet_format, statmsg2)
                    rate_send_buffer+= statspacket2
                    
                    rate_msg2 = (94, mac_id, NEventsSent0, NEventsSent1, deltaT, wno, Ms, subMs, NEventsSentBoth, null_count)
                    rate_packet2 = data_packing(send_packet_format, rate_msg2)
                    rate_send_buffer+= rate_packet2
                    NEvents0=NEvents1=NEventsSent0=NEventsSent1=deltaT=ch0_null_count=ch1_null_count=NEventsSentBoth=rx_count = null_count = unreas_count= 0
                    loop_time= []
                    proc_time = []
                    request_bunching = []
                    transit_time_list= []
                    if len(rate_send_buffer)>0: #If not none
                        send_data(rate_send_buffer)
                        rate_send_buffer = bytearray()

                        T0=T1

                        #print('buffer size ',uart1.any(), 'bytes\n')
                        #print("Rate packet sent")

                    else:
                        print("Continued from rate")
                        continue  #Do not break here
            T_loop_e = time.ticks_us()
            loop_time.append(time.ticks_diff(T_loop_e, T_loop_s))
            #print("Loop time:", time.ticks_diff(T_loop_e, T_loop_s))
        else:
            continue # Continue main loop if data not recieved

    except Exception as e:
        sys.print_exception(e)
        print("Main loop exception:", e)
        error_msg = (100, mac_id, 1, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        continue

        
        





