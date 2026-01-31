#Airshower Main
#Updated- 10-28-25 (Sent from Jean-Luc)

# OTA Update is working with ESP32 streaming data to Karbon Computer when I send the OTA Update from my macbook
# OTA update is unreliable when sent from Karbon computer

#Changelog:
    #Altered diff in request function
    #Fixed error in how sockets were reconnecting
    #
from machine import UART, Pin, WDT
import socket
import ustruct
import time
import network
import gc
import random
#import errno
#import ota_update
import _thread
from sys import exit as exit
#---------GPS Functions-----------
#print(gc.mem_free())
#gc.collect()
#gc.enable()
#gc.threshold(40000)
print("free mem", gc.mem_free())

#UBX_HDR = b'\xb5\x62' # \xb5\x62
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
#We can increase the buffer size to 64kB by creating a ring buffer
#See ChatGPT: ESP32 Rx Buffer Limit on 1/19/2026
#exit()

time.sleep(0.1)
#NNC=10
numMeas=1
global tcoll0
tcoll0=0
# ---------- Wi-Fi Setup ----------
Location='AS'
print(Location)
if Location == 'Oxy':
   ssid = 'ONet'
   password = ''
   HOST='134.69.216.235'
elif Location == 'AS':
   ssid = 'AirShower2.4G'
   password = 'Air$shower24'
   HOST='134.69.77.61'
else:
    print(Location,'not found')

#These can be moved to the main wifi function, but I thinks its more versitile to define them as globals
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
#wlan.ifconfig(('169.254.241.89', '255.255.0.0', '134.69.192.7', '134.69.192.7'))  # Example; use a free IP, correct subnet/gateway/DNS
#wlan.ifconfig(('10.0.0.7', '255.255.255.0', '10.0.0.1', '10.0.0.1'))  # Example; use a free IP, correct subnet/gateway/DNS
mac_id = wlan.config('mac')[-1]  # last byte of MAC
#print(type(mac_id))
print('mac id:', mac_id)

PORT = 12345

#Socket Stuff

# ---------- Functions ----------
wdt = WDT(timeout=20000)

#---------OTA Function------------

def start_listener():
  try:  
    addr = socket.getaddrinfo('0.0.0.0', 8080)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Listening for OTA trigger on port 8080...")

    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024)
        request = str(request)

        if "/ota" in request:
            print("OTA trigger received")
            cl.send("HTTP/1.1 200 OK\r\n\r\nUpdating...\n")
            ota_update.download_and_install(cl)
        else:
            print("No OTA trigger received")
            cl.send(b"HTTP/1.1 200 OK\r\n\r\nHello from ESP32\n")
            cl.close()
  except exception as e:
      print('start_listener error:',e)


#It clears 500bytes in 100 + 500 = 600us --> t = (100+Nbytes)us
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
        print("clearRxBuffer error:",e)
        #error_msg = (100, mac_id, 1, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
        pass

def con_to_wifi(ssid, password):
  print("con_to_wifi")
  try:
    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(0.5)
    
    while not wlan.isconnected():
        try:
            print("Connecting to Wi-Fi...")
            wlan.connect(ssid, password)
            time.sleep(.5)
            #print("1 sec delay")
            while not wlan.isconnected():
                time.sleep(0.1)
            print("Wi-Fi connected.")
            return wlan.ifconfig()
        except Exception as e:
 #           time.sleep(.5)
            #print(f"Connection attempt failed: {e}")
            #error_msg = (100, mac_id, 6, 0, 0, 0, 0, 0, 0)
            #packet = data_packing(send_packet_format, error_msg)
            #s.send(packet)
            pass
        
  except Exception as e:
      print("con_to_wifi error:", e)

def connect_socket(host, port):
  try:
    print("socket connecting to ", host,port)
    s = socket.socket()
    try:
        s.connect((host, port))
        print("Socket connected.")
        wdt.feed()
        #clearRxBuf()
        return s
    except Exception as e:
        print("Failed to connect socket:", e)
        print(gc.mem_free())
        #error_msg = (100, mac_id, 8, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
  except Exception as e:
      print("connect_socket: error", e)


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
        print("Error in data packing", e)
        #error_msg = (100, mac_id, 7, 0, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
        
def reconnect_socket(sock):
    try:
        if sock:
            sock.close()
    except Exception as e:
        print("Error closing socket:", e)
        error_msg = (100, mac_id, 9, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
    time.sleep(.1)
    return connect_socket(HOST, PORT)

def clear_wifi_rx_buffer(sock):      
    if not sock:
        print("No socket to clear.") 

    try:
        
        data = sock.recv(1024)
     
        print("Wifi RX buffer cleared of:", len(data), "bytes")
    except Exception as e:
        print("Error during buffer clear:", e)
        error_msg = (100, mac_id, 10, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        


# ---------- GPS Functions ----------


def maxRxBuf(n):
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    #print('maxRxBuf')
    try:
        while (uart1.any() > (n )):
            nskim = uart1.any()-n + 1000
            print('buffer cleared of ',nskim, 'bytes\n')
            (uart1.read(nskim))
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[];
        towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print('maxRxbuf exception',e)
        error_msg = (100, mac_id, 2, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)

# def findUBX_HDR():
# 
#         #print('findUBX_HDR')
#         Byte2=0
#         while Byte2 != b'\x62':
#             while uart1.any() < 1:
#                 time.sleep_ms(1)
#             Byte1 = uart1.read(1)[0]
#             while Byte1 != b'\xb5':
#                 #print('.',end='')
#                 while uart1.any() < 1:
#                     time.sleep_ms(1)
#                 Byte1 = uart1.read(1)
#                 #pass
#             while uart1.any() < 1:
#                 time.sleep_ms(1)
#             Byte2=uart1.read(1)

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

  except Exception as e:
    print("findUBX_HDR error:",e)
    error_msg = (100, mac_id, 3, 0, 0, 0, 0, 0, 0)
    packet = data_packing(send_packet_format, error_msg)
    s.send(packet)

# def findHDR2():
#     while uart1.any() < 4:
#         time.sleep_ms(1)
#     data0 = uart1.read(4)
#     #print('Header: ',data0)
#     bytehdr2 = data0[0:2]
#     lenb = data0[2:4]
#     leni = int.from_bytes(lenb, "little")
#     return(bytehdr2, leni)

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
        error_msg = (100, mac_id, 4, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        return None

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
        print("Error in readData:", e)
        return (0, 0, 0, 0)





# def readData(det):
#   global bytehdr2, slope
#   try:
# #    print("buffer size:",uart1.any())
#     findUBX_HDR()
# 
#     bytehdr2, leni = findHDR2()
#     if leni > 2048:
#         return((0,0,0,0))
# 
#     while uart1.any() < (leni+2):
#         time.sleep_ms(1)
#        
#     if (bytehdr2 == RXM_TM):
#             plb = uart1.read(leni)
#             cksum = uart1.read(2)
#             version=plb[0]
#             numMeas=plb[1]
#             for ii in range(0, numMeas*24, 24):
#                 edgeInfob=plb[8+ii:12+ii]
#                 edgeInfo=int.from_bytes(edgeInfob, "little")
#                 RF= (edgeInfo >> 4) & 1
#                 ch = edgeInfo & 1
#                 countb = plb[12+ii:14+ii]
#                 count=int.from_bytes(countb, "little")
#                 wnob=plb[14+ii:16+ii]
#                 wno=int.from_bytes(wnob,"little")
#                 towMsb=plb[16+ii:20+ii]
#                 towMs=int.from_bytes(towMsb,"little")
#                 towSubMsb=plb[20+ii:24+ii]
#                 towSubMs=int.from_bytes(towSubMsb,"little")
#                 RFRaw.append(RF)
#                 chRaw.append(ch)
#                 countRaw.append(count)
#                 towMsRaw.append(towMs)
#                 towSubMsRaw.append(towSubMs)
# #            print("endif RXM_TM",time.time_ns(),"ns")
# 
#     elif (bytehdr2 == TIM_TM2):
# #           print("   if TIM_TM",time.time_ns(),"ns")
#             plb = uart1.read(leni)
#             cksum = uart1.read(2)
#             ch=plb[0]
#             edgeInfo=plb[1]
#             edgeF = (edgeInfo >> 2) & 1
#             edgeR = (edgeInfo >> 7) & 1
#             timeValid = (edgeInfo >> 6) & 1
#             countb = plb[2:4]
#             count=int.from_bytes(countb, "little")
#             wnoRb = plb[4:6]
#             wnoR=int.from_bytes(wnoRb, "little")
#             wnoFb = plb[6:8]
#             wnoF=int.from_bytes(wnoFb, "little")
#             towMsRb=plb[8:12]
#             towMsR=int.from_bytes(towMsRb,"little")
#             towSubMsRb=plb[12:16]
#             towSubMsR=int.from_bytes(towSubMsRb,"little")
#             towMsFb=plb[16:20]
#             towMsF=int.from_bytes(towMsFb,"little")
#             towSubMsFb=plb[20:24]
#             towSubMsF=int.from_bytes(towSubMsFb,"little")
#             accEstb=plb[24:28]
#             accEst=int.from_bytes(accEstb,"little")
#             if det == 1:
#                 countCal.append(count)
#                 #print("*****lengths of towMsCal and towSubMsCal", len(towMsCal),len(towSubMsCal), towMsR, towSubMsR)
#                 towMsCal.append(towMsR)
#                 towSubMsCal.append(towSubMsR)
#                 #print("*****lengths of towMsCal and towSubMsCal", len(towMsCal),len(towSubMsCal))
#                 #print("endif TIM_TM",time.time_ns(),"ns")
#                 return (wnoR, towMsR, towSubMsR, timeValid)
#             
#             if det==0:
#                 return[
#                     (0, 1, ch, wnoR, towMsR, towSubMsR),
#                     (1, 1, ch, wnoF, towMsF, towSubMsF)
#                 ]
# 
#     elif (bytehdr2 == NAV_CLOCK):
#             #print("   if NAV_CK",time.time_ns(),"ns")
#             plb = uart1.read(leni)
#             cksum = uart1.read(2)
#             iTOWb = plb[0:4]
#             iTOW=int.from_bytes(iTOWb, "little")
#             iclkBiasb = plb[4:8]
#             iclkBias=ustruct.unpack('<i',iclkBiasb)[0]
#             iclkDriftb = plb[8:12]
#             iclkDrift=ustruct.unpack('<i',iclkDriftb)[0]
#             tAccb = plb[12:16]
#             tAcc=int.from_bytes(tAccb, "little")
#             fAccb = plb[16:20]
#             fAcc=int.from_bytes(fAccb, "little")
#             #print("      NAV_CLOCK",time.time_ns(),"ns")
#             #print(f"iTOW: {iTOW:d}, iclkBias: {iclkBias:d}, iclkDrift: {iclkDrift:d}, tAcc: {tAcc:d}, fAcc: {fAcc:d} ")
#             slope = iclkDrift
#             print('** slope =', slope)
#             #print("endif NAV_CLOCK",time.time_ns(),"ns")
#     return (0,0,0,0)
#     
#   except Exception as e:
#         print("Error in readData:",e)
#         #error_msg = (100, mac_id, 5, 0, 0, 0, 0, 0, 0)
#         #packet = data_packing(send_packet_format, error_msg)
#         #s.send(packet)
#     



    

# ---------- Connecting to Server ----------



    

# ---------- Main Loop ----------

if con_to_wifi(ssid, password):
#    _thread.start_new_thread(start_listener, ())
    print("No OTA listener started in background.")
else:
    print("Wi-fi connection failed.")
ip, subnet, gateway, dns = wlan.ifconfig()
ip_last_byte = int(ip.split('.')[-1])           # NEED TO PRINT THE ENTIRE IP ADDRESS HERE?
print("ESP IP:", ip_last_byte)
print(type(ip_last_byte))
print(ip)

s = connect_socket(HOST,PORT)
time.sleep(2)
#s.setblocking(False) #SOme blocking may be good. I want the code to wait for data, but not to wait when sending. Maybe there is a good medium here.
s.settimeout(.1)

send_packet_format = "!iiiiiiiiii"
request_packet_format = '!iiiii'


time.sleep(1)
clearRxBuf()
clear_wifi_rx_buffer(s)
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
    
clearRxBuf()
# 5 seconds
#print("Running")

error_msg = (100, mac_id, 15, time.ticks_ms(), ip_last_byte, 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, error_msg)
s.send(packet)

NEvents0 = 0
NEvents1 = 0
deltaT0 = 0
deltaT1 = 0
T0=T1=0
NEventsSent0=0
NEventsSent1=0
T0=time.ticks_us()

array_count = 0
Rate0=0
Rate1=0
R0index=[]
R1index=[]
global toi_len
while True:
    print("1")

    try:
            # Ensure Wi-Fi stays connected
        if not wlan.isconnected():
            print("Wi-Fi disconnected. Reconnecting...")
            con_to_wifi(ssid, password)
        maxRxBuf(20000) #Make sure buffer isnt full before recieving
        try:
#            print('buffer size ',uart1.any(), 'bytes\n')
            #print("2")
            pass
            req = s.recv(20) #Dont need poller, can just check for socket activity on a not blocking socket
            time.sleep_ms(1)
            #print("Data received:", len(req))
            #print('buffer size ',uart1.any(), 'bytes\n')

        except Exception:
            #print("Error receiving")
            #error_msg = (100, mac_id, 11, 0, 0, 0, 0, 0, 0, 0)
            #packet = data_packing(send_packet_format, error_msg)
            #s = reconnect_socket(s)
            #s.send(packet)

            continue
#        if True:
        if req:
            try:
                inst, w_num, ms, sub_ms, event_num = ustruct.unpack(request_packet_format, req) #There might be an error here. What if multiple messages came in at the same time and I read them all at the same time? Will they be lost as ustruct may only evaluate the first little bit?
                #inst=99
                #event_num=99
                print("3")
            except Exception as e:

                print("Error unpacking request:", e)
                error_msg = (100, mac_id, 12, 0, 0, 0, 0, 0, 0, 0)
                packet = data_packing(send_packet_format, error_msg)
                s.send(packet)
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
                

                print("GPS request...")
                print('buffer size ',uart1.any(), 'bytes\n')
                #print('free mem before request:', gc.mem_free())
#                timesOfInterest = request(-1,100,0)
                RF,cal,ch,w_num,ms,sub_ms = request(w_num, ms, sub_ms)
#                RF,cal,ch,w_num,ms,sub_ms = request(-1,100,0)
#                RF,cal,ch,w_num,ms,sub_ms = request(-1,100,0)
                #print('free mem after request:', gc.mem_free())
#                timesOfInterest = request(w_num, ms, sub_ms)
                #print("4")
#                if RF is None or len(RF)==0:
                if  toi_len == 0:
                    msg = (99, mac_id, 0, 0, 0, 0, 0, 0, event_num, array_count)


                    packet = data_packing(send_packet_format, msg)
                    try:
                        #pass
                        s.send(packet)
                        #print('********',msg)
                    except Exception as e:
                        print("send error",e)
                        s = reconnect_socket(s)
                    array_count+=1
                    wdt.feed()
                    continue
                
                #print(timesOfInterest)
                #print('free mem before for loop:', gc.mem_free())

                print("7")
#                rf,cal,ch,wno,ms,subms
                #print("len(RF)",len(RF))
                for i in range(toi_len):
#                     inst = 99           
#                     ID = mac_id
#                     RF = timesOfInterest[i][0]              
#                     cal = timesOfInterest[i][1]               
#                     ch = timesOfInterest[i][2]           
#                     w_num = timesOfInterest[i][3]   
#                     ms = timesOfInterest[i][4]      
#                     sub_ms = timesOfInterest[i][5]
#                     event_num = event_num #Unnecessary
                    count = array_count #timesOfInterest[i][6]
                    
                    msg = (99, mac_id, RF[i], cal[i], ch[i], w_num[i], ms[i], sub_ms[i], event_num, count)
#                    msg = (inst, ID, RF, cal, ch, w_num, ms, sub_ms, event_num, count)
                    print(msg)
                    packet = data_packing(send_packet_format, msg)
                    print("5")
                    try:
                        #if (0): #(RF==0)& (ch==1)&(random.randint(0,10)==1):
                        s.send(packet) #Should I start checking wifi and socket are active before sending? It seems kind of pointless,
                                        #I would have to reconnect to them anyway if it I wasnt and w
                        print("sent packet")
                        #array_count+=1
                        if RF==0:
                            if ch==0:
                                NEventsSent0 +=1
                            if ch==1:
                                NEventsSent1 +=1
                        #NEvents2+=1
                        wdt.feed()
                        print('buffer size ',uart1.any(), 'bytes\n')
                        print("data sent")
                        print('Rates:',Rate0, Rate1)

                        print("6")
                    except Exception as e:
                        print("Send error2:", e)
                        error_msg = (100, mac_id, 13, 0, 0, 0, 0, 0, 0, 0)
                        packet = data_packing(send_packet_format, error_msg)
                        s = reconnect_socket(s)
                        s.send(packet)

                        break  # Exit inner loop

                #print('free mem after for loop:', gc.mem_free())

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
            
                if T1-T0 > 5000000:
                    print('NEvents')
#                    T1=time.ticks_us()
                    uart1.write(POLL_NAV_CLOCK)
                    Rate0 = round((NEvents0*1000000000)/(deltaT0+1e-9))
                    Rate1 = round((NEvents1*1000000000)/(deltaT1+1e-9))
                    RateSent0 = round(NEventsSent0*1000000/(T1-T0)*1000)
                    RateSent1 = round(NEventsSent1*1000000/(T1-T0)*1000)
                    print('*Rate0:',Rate0)
                    print('*Rate1:',Rate1)
                    print('*RateSent0:',RateSent0)
                    print('*RateSent1:',RateSent1)
                    NEvents0 =NEvents1=NEventsSent0=NEventsSent1=deltaT0=deltaT1=0
                    T0=T1
                    #exit()                   
                    msg = (99, mac_id, 19, Rate0+Rate1, RateSent0+RateSent1, 0, 0, 0, 0, 0)
                    rate_packet = data_packing(send_packet_format, msg)
                    try:
                        print("s.send")
                        s.send(rate_packet)
                        print("data sent")
                        wdt.feed()
                        print('buffer size ',uart1.any(), 'bytes\n')

                        print("data sent")
                    except Exception as e:
                        print("error in rate calc",e)
                        s = reconnect_socket(s)
                        #break  # Exit inner loop
                        continue

    except Exception as e:
        print("Main loop exception:", e)
        #exit()
        error_msg = (100, mac_id, 14, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        print("Error sent")
        continue

        
        


