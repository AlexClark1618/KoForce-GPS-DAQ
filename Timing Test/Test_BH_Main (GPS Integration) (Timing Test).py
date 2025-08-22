#Borehole
#8-18-25

import socket
import ustruct
import time
import network
import select
from machine import UART, Pin, WDT
import time
import gc

#---------GPS Functions-----------
UBX_HDR = b'\xb5b'
RXM_TM=b'\x02\x74'
TIM_TM2=b'\x0d\x03'
uart1_tx_pin = 12  # Example: GPIO12
uart1_rx_pin = 14  # Example: GPIO14
uart1 = UART(1, baudrate=115200*4, tx=Pin(uart1_tx_pin), rx=Pin(uart1_rx_pin), rxbuf=8192)


time.sleep(1)
#while(1):
NNC=10
numMeas=1

def clearRxBuf():
    while uart1.any():
        print('buffer cleared of ',uart1.any(), 'bytes\n')
        (uart1.read())

def findUBX_HDR():
    while  (uart1.read(1) != b'\xb5'):
        pass
    while  (uart1.read(1) != b'\x62'):
        pass
    #        C   ID  RF Cal  ch wno  Ms Sub cnt
    #request=(0,  0,  0,  0,  0,  0,  0,  0,  0)

def request(wno,Ms,subMs):
    gc.collect()
    res=(0,0,0)
    while res[1] < Ms+1: #Exceed the time of interest by at least 1 ms    
        res=readData(1)
        if res[0] != 0:
            #print(res[0] == 0)
            print ('read Cal Data',res)
            if (abs(Ms - res[1]) > 1000) | (res[0] != wno) :
                print('Unreasonable request')
                return([(0,0,0,0,0,0)])
    lastC=len(countCal)-1
    lastR=len(countRaw)-1
    #Find upper index in raw data
    for i in range(lastR,-1,-1):
        if countRaw[i]==countCal[lastC]:
            break
    rawIndex2=i
    #Find lower index in raw data
    for i in range(lastR-1,-1,-1):
        if countRaw[i]==countCal[lastC-1]:
            break
    rawIndex1=i
    
    tCal2=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
    tCal1=towMsCal[lastC-1]*1000000+(towSubMsCal[lastC-1])
    tRaw2=towMsRaw[rawIndex2]*1000000+int(towSubMsRaw[rawIndex2]/1000)
    tRaw1=towMsRaw[rawIndex1]*1000000+int(towSubMsRaw[rawIndex1]/1000)
        
    #slope = (tCal2-tCal1)/(tRaw2-tRaw1)
    #print('slope', slope)
    intercept = tCal2-tRaw2
    timesOfInterest=[]
    for i in range(rawIndex1,rawIndex2+1):
        tRaw=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
        print(towMsRaw,towSubMsRaw,intercept,tRaw)
        res=tRaw+intercept
        sec=int(res/1000000000)
        ns=res-sec*1000000000
        ms=int(ns/1000000)
        Ms=sec*1000+ms
        SubMs=res-Ms*1000000
        timesOfInterest.append((RFRaw[i],1,chRaw[i],wno,Ms,SubMs))
    return(timesOfInterest)

def readData(det):
#det: 0 == BH and 1 == AS
#     towMsR=0
#     while towMsR < Request:
        
        #print('readData')
        findUBX_HDR()    
        #print('\tFound UBX header: ', bytehdr)
        #bytehdr = UBX_HDR
        while uart1.any() < 4:
            pass
        data0 = uart1.read(4)
        #print('Header: ',data0)
        bytehdr2 = data0[0:2]
        lenb = data0[2:4]
        if bytehdr2 == RXM_TM:
            hdr2='RXM_TM'
            ##print('\tFound Raw time stamp header: ', bytehdr2)
        elif bytehdr2 == TIM_TM2:
            hdr2='TIM_TM2'
            ##print('\tFound Calibrated time stamp header: ', bytehdr2)

        leni = int.from_bytes(lenb, "little")
        ##print('\tdata length: ',leni)
        ##print ('buffer ', uart1.any())
        while uart1.any() < (leni+2):
            pass

        if (bytehdr2 == RXM_TM):
                plb = uart1.read(leni)
                #print(plb)
                cksum = uart1.read(2)
                #print('checksum:',cksum)
                version=plb[0]

                end="   "
                ##print('\nraw data:\n', bytehdr+bytehdr2+plb+cksum, '\n')

                ##print ('parsed data:')
                ##print(hdr+'|'+hdr2)
                #print('ver',version, end=end)
                numMeas=plb[1]
                #print('numMeas',numMeas, end ="\t")
                for ii in range(0, numMeas*24, 24):
                    #print('ii',ii,end=end)
                    edgeInfob=plb[8+ii:12+ii]
                    #print('edgeInfob',edgeInfob)
                    edgeInfo=int.from_bytes(edgeInfob, "little")
                    #print('edgeInfo',edgeInfo, end =end)
                    RF= (edgeInfo >> 4) & 1
                    #if RF ==1:
                        #print('EdgeF', end =end)
                    #else:
                        #print('EdgeR', end =end)
                    ch = edgeInfo & 1
                    ##print('channel ', ch, end =end)
                    countb = plb[12+ii:14+ii]
                    count=int.from_bytes(countb, "little")
                    ##print('count ', count, end =end)
                    wnob=plb[14+ii:16+ii]
                    wno=int.from_bytes(wnob,"little")
                    ##print('wno ', wno, end =end)
                    towMsb=plb[16+ii:20+ii]
                    towMs=int.from_bytes(towMsb,"little")
                    ##print('towMs ', towMs, end =end)
                    towSubMsb=plb[20+ii:24+ii]
                    towSubMs=int.from_bytes(towSubMsb,"little")
                    ##print('towSubMs ', towSubMs)
                ##print('\n')
#                     RFRaw.append(RF)
#                     chRaw.append(ch)
#                     countRaw.append(count)
#                     towMsRaw.append(towMs)
#                     towSubMsRaw.append(towSubMs)
        elif (bytehdr2 == TIM_TM2):
                plb = uart1.read(leni)
                #print(plb)
                cksum = uart1.read(2)
                #print('checksum:',cksum)

                end="   "
                ##print('\nraw data:\n', bytehdr+bytehdr2+plb+cksum, '\n')

                ##print ('parsed data:')
                ##print(hdr+'|'+hdr2)
                #print('ver',version, end=end)
                ch=plb[0]
                ##print('channel ',channel, end=end)
                edgeInfo=plb[1]
                #print('edgeInfo',edgeInfo, end = end)
                #edgeInfo=int.from_bytes(edgeInfob, "little")
                edgeF = (edgeInfo >> 2) & 1
                edgeR = (edgeInfo >> 7) & 1
                timeValid = (edgeInfo >> 6) & 1
                #timeValid = int.from_bytes(timeValidb, "little")
                ##print('timeValid', timeValid, end=end)
                countb = plb[2:4]
                count=int.from_bytes(countb, "little")
                ##print('count ', count, end =end)
                wnoRb = plb[4:6]
                wnoR=int.from_bytes(wnoRb, "little")
                ##print('wnoR ', wnoR, end =end)
                wnoFb = plb[6:8]
                wnoF=int.from_bytes(wnoFb, "little")
                ##print('wnoF ', wnoF, end =end)
                towMsRb=plb[8:12]
                towMsR=int.from_bytes(towMsRb,"little")
                ##print('towMsR ', towMsR, end=end)
                towSubMsRb=plb[12:16]
                towSubMsR=int.from_bytes(towSubMsRb,"little")
                ##print('towSubMsR ', towSubMsR, end=end)
                towMsFb=plb[16:20]
                towMsF=int.from_bytes(towMsFb,"little")
                ##print('towMsF ', towMsF, end=end)
                towSubMsFb=plb[20:24]
                towSubMsF=int.from_bytes(towSubMsFb,"little")
                ##print('towSubMsF ', towSubMsF, end=end)
                accEstb=plb[24:28]
                accEst=int.from_bytes(accEstb,"little")
                ##print('accEst ', accEst, end=end)
                
                ##print('\n')
                
                #cksum = uart1.read(2)
                #print('checksum',cksum,'\n')
                if det == 1:
                    RFRaw.append(0)
                    chRaw.append(ch)
                    countCal.append(count)
                    towMsCal.append(towMsR)
                    towSubMsCal.append(towSubMsR)

        else:
                ##print('It is junk')
                
                while uart1.any():
                    print('buffer cleared of ',uart1.any(), 'bytes\n')
                    (uart1.read())
        
        if (bytehdr2 == TIM_TM2) & (det == 1):
            return((wnoR,towMsR,towSubMsR)) #calibrated data
        elif (bytehdr2 == TIM_TM2) & (det == 0):
            print(ch, wnoR, wnoF, towMsR, towMsF, towSubMsR, towSubMsF)

            return [
                (0, 1, ch, wnoR, towMsR, towSubMsR),
                (1, 1, ch, wnoF, towMsF, towSubMsF)
            ]
        else:
            return((0,0,0))
# ---------- Functions ----------
max_retries=5
delay=1
def con_to_wifi(ssid, password):
    '''
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            time.sleep(1)
    print("Wi-Fi connected.")
    return None
    '''
    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(0.1)
    
    retries = 0
    while retries < max_retries:
        try:
            print("Connecting to Wi-Fi...")
            wlan.connect(ssid, password)
            while not wlan.isconnected():
                time.sleep(1)
            print("Wi-Fi connected.")
            return wlan.ifconfig()
        except OSError as e:
            print(f"Connection attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < max_retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                wdt.feed()

            else:
                print("Max retries reached. Could not connect to Wi-Fi.")
                return None
            
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

# ---------- Wi-Fi Setup ---------
#ssid = 'TP-Link_FB80'
#password = 'Beau&River'

ssid = 'ONet'
password = ''

#These can be moved to the main wifi function, but I thinks its more versitile to define them as globals
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

con_to_wifi(ssid, password)
full_mac = wlan.config('mac')
mac_id = wlan.config('mac')[-1]  # last byte of MAC
print(full_mac)
print(mac_id)

# ---------- Connecting to Server ----------
#HOST = '192.168.0.93' #Home
HOST = '134.69.200.155'
PORT = 12345

s = connect_socket(HOST,PORT)

# ---------- For peeking ----------
#poller = select.poll()
#poller.register(s, select.POLLIN)

# ---------- Main Loop ----------
clearRxBuf()

event_num = 0 #Keeps track of borehole events (could be moved to server)

wdt = WDT(timeout=3000)  # 5 seconds
print("Running")
while True:
    #Checks for wifi disconnections. (May want to move this to an exception handle)
    wifi_s = time.ticks_us()
    if not wlan.isconnected():
        con_to_wifi(ssid, password)
    wifi_f = time.ticks_us()
    
    print("Time to connect to wifi:", time.ticks_diff(wifi_f, wifi_s))
    
    #Checks if activity of socket
#    events = poller.poll(0)
#     if events:
#         req = s.recv(1024)
#         print("You got data!")

    #Reading data from gps
    # RFRaw=[]
    # chRaw=[]
    # countRaw=[]
    # countCal=[]
    # towMsRaw=[]
    # towMsCal=[]
    # towSubMsRaw=[]
    # towSubMsCal=[]
    
    toi_s = time.ticks_us()
    res = (0,0,0)
    while res[0] == 0:
        res = readData(0)
        #print(res)
    #print('res:', res)
    timesOfInterest = res
    toi_f = time.ticks_us()
    print("Time to find toi:", time.ticks_diff(toi_f, toi_s))

    ID=mac_id
    
    toSend=[]
    toSend_s = time.ticks_us()

    for i in range(len(timesOfInterest)):
        print(timesOfInterest[i][0])
        toi = (99, ID,
               timesOfInterest[i][0],
               timesOfInterest[i][1],
               timesOfInterest[i][2],
               timesOfInterest[i][3],
               timesOfInterest[i][4],
               timesOfInterest[i][5],
               event_num)
        toSend.append(toi)
    toSend_f = time.ticks_us()
    print("Time to assemble toSend:", time.ticks_diff(toSend_f, toSend_s))

    ###Jean-Luc's Request function goes here###
        #We will expect to send 4 packets each is a tuple in a larger list. This will represent the rise and fall 
        #of the signal and encoding. Should edit the package function to pack these tuples 

    for tup in toSend:
        data_s = time.ticks_us()

        inst = tup[0]           
        ID = tup[1]
        RF = tup[2]              
        cal = tup[3]               
        ch = tup[4]           
        w_num = tup[5]    
        ms = tup[6]       
        sub_ms = tup[7]
        event_num = tup[8] #Unnecessary 

        try:
            packet = data_packing(packet_format)
            data = s.send(packet)
            data_f = time.ticks_us()
            print("Time to send data:", time.ticks_diff(data_f, data_s))
            wdt.feed()

            #gc.collect()
            #print(f'Bytes sent: {data}') #Prints byte size
        
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
        print(".")
        
        #time.sleep(1)
    

    

