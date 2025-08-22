#Airshower
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
uart1 = UART(1, baudrate=115200*4, tx=Pin(uart1_tx_pin), rx=Pin(uart1_rx_pin), rxbuf= 8192*2)


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
    #print('Request Started')
    #print(gc.mem_free())
    gc.collect()
    res=(0,0,0)
    while res[1] < Ms+1: #Exceed the time of interest by at least 1 ms
        #print('readData started')
        res=readData(1)
        #print('readData finished')
        #print('readData output:', res)
        #print(Ms)
        #print(res)
        if res[0] != 0:
            #print(res[0] == 0)
            #print ('read Cal Data',res)
            if (abs(Ms - res[1]) > 1) | (res[0] != wno) :
                pass
                #print('Unreasonable request')
                 #Assuming we get a res > Ms and fails this check it should reset it

                #clearRxBuf()
                #return [(0,0,0,0,0,0)]
            
    lastC=len(countCal)-1
    lastR=len(countRaw)-1
    #Find upper index in raw data

    for i in range(lastR,-1,-1):
        if countRaw[i]==countCal[lastC]:
            break
    rawIndex2=i
    #Find lower index in raw data
    for j in range(lastR-1,-1,-1):
        if countRaw[j]==countCal[lastC-1]:
            break
    rawIndex1=j
    #print('towMsCal:',towMsCal)
    #print('towSubMsCal:',towSubMsCal)

    tCal2=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
    tCal1=towMsCal[lastC-1]*1000000+(towSubMsCal[lastC-1])
    tRaw2=towMsRaw[rawIndex2-1]*1000000+int(towSubMsRaw[rawIndex2-1]/1000)
    tRaw1=towMsRaw[rawIndex1-1]*1000000+int(towSubMsRaw[rawIndex1-1]/1000)
        
    slope = (tCal2-tCal1)/(tRaw2-tRaw1)
    #print('slope', slope)
    #intercept = tCal2-tRaw2
    timesOfInterest=[]
    for i in range(rawIndex1,rawIndex2+1):
        tRaw=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
        #print(towMsRaw,towSubMsRaw,intercept,tRaw)
        res=int((tRaw-tRaw1)*slope)+tCal1
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
        
        #print('readData started')
        findUBX_HDR()
        #print('found header')
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
            #print('1')
            #print('\tFound Raw time stamp header: ', bytehdr2)
        elif bytehdr2 == TIM_TM2:
            hdr2='TIM_TM2'
            #print('2')
            #print('\tFound Calibrated time stamp header: ', bytehdr2)

        leni = int.from_bytes(lenb, "little")
        #print('\tdata length: ',leni)
        ##print ('buffer ', uart1.any())

        while uart1.any() < (leni+2):
            #print('3')
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
                    #print('towSubMs ', towSubMs)
                ##print('\n')
                    RFRaw.append(RF)
                    chRaw.append(ch)
                    countRaw.append(count)
                    towMsRaw.append(towMs)
                    towSubMsRaw.append(towSubMs)
                    #print('4')
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
                #print('accEst ', accEst, end=end)
                #print('5')
                ##print('\n')
                
                #cksum = uart1.read(2)
                #print('checksum',cksum,'\n')
                if det == 1:
                    RFRaw.append(0)
                    chRaw.append(ch)
                    countCal.append(count)
                    towMsCal.append(towMsR)
                    towSubMsCal.append(towSubMsR)
                    #print('6')
        else:
                #print('It is junk')
                
                while uart1.any():
                    #print('buffer cleared of ',uart1.any(), 'bytes\n')
                    (uart1.read())
                    
        if (bytehdr2 == TIM_TM2) & (det == 1):
            #print('data bytehdr2',bytehdr2)

            return((wnoR,towMsR,towSubMsR)) #calibrated data
        elif (bytehdr2 == TIM_TM2) & (det == 0):
            #print(ch, wnoR, wnoF, towMsR, towMsF, towSubMsR, towSubMsF)

            return[
                (0, 1, ch, wnoR, towMsR, towSubMsR),
                (1, 1, ch, wnoF, towMsF, towSubMsF)
            ]
        else:
            #print('0 bytehdr2',bytehdr2)
            #if bytehdr2 == RXM_TM:
                #print('Header passed')
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
 
send_packet_format = "!IIIIIIIII"
request_packet_format = '!IIIII'

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
#ssid = 'TP-Link_FB80'
#password = 'Beau&River'

ssid = 'ONet'
password = ''

#These can be moved to the main wifi function, but I thinks its more versitile to define them as globals
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

con_to_wifi(ssid, password)
mac_id = wlan.config('mac')[-1]  # last byte of MAC
print('mac id:', mac_id)
# ---------- Connecting to Server ----------
#HOST = '192.168.0.93' #Home
HOST = '134.69.200.155'
PORT = 12345

s = connect_socket(HOST,PORT)

# ---------- For peeking ----------
poller = select.poll()
poller.register(s, select.POLLIN)

# ---------- Main Loop ----------


clear_rx_buffer(s,poller)

i = 0
while i < 20:
    clearRxBuf()
    time.sleep(0.1)
    i += 1

wdt = WDT(timeout=10000)  # 5 seconds
print("Running")
while True:
    #Checks for wifi disconnections. (May want to move this to an exception handle)
    wifi_s = time.ticks_us()
    if not wlan.isconnected():
        con_to_wifi(ssid, password)
    wifi_f = time.ticks_us()
    
    print("Time to connect to wifi:", time.ticks_diff(wifi_f, wifi_s))  

    poll_s = time.ticks_us()
    event = poller.poll(1) #Checks for socket activity
    poll_f = time.ticks_us()

    print("Poll time:", time.ticks_diff(poll_f,poll_s))

    try:
        if event:
            read_s = time.ticks_us()
            req = s.recv(1024) #Request from server
            read_f = time.ticks_us()
            print("Time to read data from buffer:", time.ticks_diff(read_f,read_s))

            if req: #If request proceed
                #print('Data present')
                try:
                    unpack_s = time.ticks_us()
                    inst, w_num, ms, sub_ms, event_num = ustruct.unpack(request_packet_format, req)
                    unpack_f = time.ticks_us()
                    print("Unpack time:", time.ticks_diff(unpack_f,unpack_s))

                except:
                    print("Error unpacking")

                #From borehole
                if inst == 99: #Processes data and collects requested integer and specified length around it                                
                    #print("w_num:" , w_num)
                    #print("ms:" , ms)
                    #print("sub_ms:" , sub_ms)
                    #print('inst successful')
                    RFRaw=[]
                    chRaw=[]
                    countRaw=[]
                    countCal=[]
                    towMsRaw=[]
                    towMsCal=[]
                    towSubMsRaw=[]
                    towSubMsCal=[]
                    
                    print('Buffer len:',uart1.any())

                    req_s = time.ticks_us()
                    timesOfInterest=request(w_num,ms,sub_ms)
                    req_f = time.ticks_us()
                    print("Time to fetch request:", time.ticks_diff(req_f,req_s))

                    #timesOfInterest = [(0,0,0,0,0,0,0,0,0)]
                    toSend=[]
                    ID = mac_id
                    
                    toSend_s = time.ticks_us()
                    for i in range(len(timesOfInterest)):
                        
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
                    #Jean-Luc's request function goes somewhere here. Will need to unpack message and put time elements into the function
                    
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
                        #print('tup broken and ready for packing')
                        try:
                            packet = data_packing(send_packet_format)
                            #for i in range(30): #Testing sending multiple packets per request
                            data = s.send(packet)
                            data_f = time.ticks_us()
                            print("Time to send data:", time.ticks_diff(data_f, data_s))
                            wdt.feed()

                            #print(f'Bytes sent: {data}')#Prints byte size
                        
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
                                #continue
                else:
                    continue
    except Exception as e:
        #print(f"Error sending to {s}:{e}")
        import sys
        sys.print_exception(e)
        
    print(".")
        
        



