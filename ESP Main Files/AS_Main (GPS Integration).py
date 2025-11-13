#Airshower Main
#Updated- 10-28-25 (Sent from Jean-Luc)
#Updated with OTA- 11-10-25 (Sent from Tim)

import socket
import ustruct
import time
import network
from machine import UART, Pin, WDT
import time
import gc
import errno
import ota_update
import _thread

#---------OTA Function------------
try:
    with open('config.txt') as f:
        detector_num = f.read().strip()
        print("This is Detector " + detector_num)
except OSError:
    detector_num = "0"  # default if not yet set
    print("No config.txt found, using default detector number:", detector_num)

version_num = "0.03"
wdt = None
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
                wdt = None  # effectively disables watchdog during OTA
                print("Watchdog disabled for OTA.")
            except Exception as e:
                print("Error disabling WDT:", e)
            
            ota_in_progress = True
            time.sleep(0.2) # check this time for timeout errors in other places
            cl.send("HTTP/1.1 200 OK\r\n\r\nUpdating...\n")
            ota_update.download_and_install(cl)
        elif "/version" in request:
            cl.send("HTTP/1.1 200 OK\r\n\r\nDetector "+ detector_num + " Version Number: " + version_num + "\n")
        else:
            cl.send(b"HTTP/1.1 200 OK\r\n\r\nHello from ESP32\n")
        cl.close()



#---------GPS Functions-----------
UBX_HDR = b'\xb5b'
RXM_TM=b'\x02\x74'
TIM_TM2=b'\x0d\x03'
uart1_tx_pin = 12  # Example: GPIO12
uart1_rx_pin = 14  # Example: GPIO14
rxbuf = (8192 * 3)
uart1 = UART(1, baudrate=115200*4, tx=Pin(uart1_tx_pin), rx=Pin(uart1_rx_pin), rxbuf= rxbuf)



time.sleep(0.1)
#NNC=10
numMeas=1

# ---------- Wi-Fi Setup ----------
ssid = 'ONet'
password = ''

#These can be moved to the main wifi function, but I thinks its more versitile to define them as globals
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

mac_id = wlan.config('mac')[-1]  # last byte of MAC
#print(type(mac_id))
print('mac id:', mac_id)

#HOST = '192.168.0.93' #Home
#HOST = '134.69.200.155'
HOST = '134.69.218.243' #Karbon Computer
PORT = 12345
#Socket Stuff

# ---------- Functions ----------
wdt = WDT(timeout=20000) # extra 0
def clearRxBuf():
    try:
        while uart1.any():
            #print('buffer cleared of ',uart1.any(), 'bytes\n')
            (uart1.read())
        RFRaw=[]
        chRaw=[]
        countRaw=[]
        countCal=[]
        towMsRaw=[]
        towMsCal=[]
        towSubMsRaw=[]
        towSubMsCal=[]
    except Exception:
        #error_msg = (100, mac_id, 1, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
        pass

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
            #print(f"Connection attempt failed: {e}")
            #error_msg = (100, mac_id, 6, 0, 0, 0, 0, 0, 0)
            #packet = data_packing(send_packet_format, error_msg)
            #s.send(packet)
            pass
        
if con_to_wifi(ssid, password):
    _thread.start_new_thread(start_listener, ())
    print("OTA listener started in background.")
else:
    print("Wi-fi connection failed.")
ip, subnet, gateway, dns = wlan.ifconfig()
ip_last_byte = int(ip.split('.')[-1])           # NEED TO PRINT THE ENTIRE IP ADDRESS HERE?
print("ESP IP:", ip_last_byte)
print(type(ip_last_byte))
def connect_socket(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        print("Socket connected.")
        wdt.feed()
        #clearRxBuf()
        return s
    except Exception as e:
        print("Failed to connect socket:", e)
        #error_msg = (100, mac_id, 8, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)

s = connect_socket(HOST,PORT)
time.sleep(1)
#s.setblocking(False) #SOme blocking may be good. I want the code to wait for data, but not to wait when sending. Maybe there is a good medium here.
s.settimeout(.05)


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
    except Exception:
        print("Error in data packing")
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
    time.sleep(1)
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
    try:
        while (uart1.any() > (n )):
            nskim = uart1.any()-n + 1000
            print('buffer cleared of ',nskim, 'bytes\n')
            (uart1.read(nskim))
        RFRaw=[]
        chRaw=[]
        countRaw=[]
        countCal=[]
        towMsRaw=[]
        towMsCal=[]
        towSubMsRaw=[]
        towSubMsCal=[]
        #return(nskim)
    except Exception:
        error_msg = (100, mac_id, 2, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)

def findUBX_HDR():
    try:
        #print('findUBX_HDR')
        Byte2=0
        while Byte2 != b'\x62':
            while uart1.any() < 1:
                pass
            Byte1 = uart1.read(1)
            while Byte1 != b'\xb5':
                #print('.',end='')
                while uart1.any() < 1:
                    pass
                Byte1 = uart1.read(1)
                pass
            #print('')
            while uart1.any() < 1:
                pass
            Byte2=uart1.read(1)
            

    except Exception:
        error_msg = (100, mac_id, 3, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        
def request(wnoToi,MsToi,subMsToi):
    try:
        resToi=MsToi*1000000+subMsToi
        gc.collect()
        res=(0,0,0,0)
        #print("res[1]", res[1])
        #print("Ms:", MsToi)
        #print("request started")
        while res[1] < MsToi: #Exceed the time of interest by at least 1 ms    
            res=readData(1)
            #print('buffer size ',uart1.any(), 'bytes\n')

            #print("res complete")
            if res[0] != 0:
                #print(res[0] == 0)
                #print ('read Cal Data',res)
                diff = MsToi - res[1]
                if (abs(diff) > 2000) | (res[0] != wnoToi) :
                    print('Unreasonable request')
                    #print("Deltat:", diff)
                    #print("Deltat:", MsToi - res[1])
                    #print('Unreasonable request')
                    error_msg = (100, mac_id, 16, diff, 0, 0, 0, 0, 0, 0)
                    packet = data_packing(send_packet_format, error_msg)
                    s.send(packet) 
                
        readData(1)
        timeValid = res[3]
        lastC=len(countCal)-1
        lastR=len(countRaw)-1
        #Find upper index in raw data
        print("countRaw:", countRaw)
        print("countCal:", countCal)
        print("lastR:",lastR)
        print("lastC:",lastC)
        print("towMsRaw:",towMsRaw[-60:])
        print("towMsCal:", towMsCal)
        #print('buffer size ',uart1.any(), 'bytes\n')

        if (lastC < 1) or (lastR < 1): #Bandaid for when there is only one calibrated data for some reason
            print('Too few elements')
            error_msg = (100, mac_id, 18, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            s.send(packet)
            return None
        
        
        rawIndex2 = None
        rawIndex1 = None


        for i in range(lastR,-1,-1):
            if countRaw[i]==countCal[lastC]:
                #print("i:", i)
                print("countRaw[i]:", countRaw[i])
                print("countCal[lastC]:", countCal[lastC])
                rawIndex2=i
                break
        print("rawIndex2:",rawIndex2)
        #Find lower index in raw data
        for i in range(lastR-1,-1,-1):
            if countRaw[i]==countCal[lastC-1]:
                #print("i:", i)
                print("countRaw[i]:", countRaw[i])
                print("countCal[lastC-1]:", countCal[lastC-1])

                rawIndex1=i
                break
        print("rawIndex1:",rawIndex1)

        
        if rawIndex1 is None or rawIndex2 is None:
            print("!!!RawIndex None!!!")
            error_msg = (100, mac_id, 17, 0, 0, 0, 0, 0, 0, 0)
            packet = data_packing(send_packet_format, error_msg)
            s.send(packet)
            return None
        
        tCal2=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
        tCal1=towMsCal[lastC-1]*1000000+(towSubMsCal[lastC-1])
        tRaw2=towMsRaw[rawIndex2]*1000000+int(towSubMsRaw[rawIndex2]/1000)
        tRaw1=towMsRaw[rawIndex1]*1000000+int(towSubMsRaw[rawIndex1]/1000)
        
        slope = (tCal2-tCal1)/(tRaw2-tRaw1)
        #print('slope', slope)
        #intercept = int(((tCal2-tRaw2)+(tCal1-tRaw1))/2)  # improved intercept
        timesOfInterest=[]
        for i in range(rawIndex1,rawIndex2+2):   #
            tRaw=towMsRaw[i]*1000000+int(towSubMsRaw[i]/1000)
    #       print(towMsRaw,towSubMsRaw,intercept,tRaw)
            res=int((tRaw-tRaw1)*slope)+tCal1
            #res=tRaw + intercept
            if ((abs(res-resToi))< 1000000):  #only keep cal data that are within 1ms of Toi.
                res2 = divmod(res, 1000000)
                #sec=int(res/1000000000)
                #ns=res-sec*1000000000
                #ms=int(ns/1000000)
                Ms=res2[0]
                SubMs=res2[1]
                if (SubMs > 999999):
                    print('*************SubMs > 999999*********')
                timesOfInterest.append((RFRaw[i],timeValid,chRaw[i],wnoToi,Ms,SubMs, countRaw[i])) 

        return(timesOfInterest)
    
    
    except Exception as e:
        print("Request error:", e)
        error_msg = (100, mac_id, 4, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        return None
    

def readData(det):
    #try:
#det: 0 == BH and 1 == AS
#     towMsR=0
#     while towMsR < Request:
    
    #print('readData started')
    #maxRxBuf(15000)
    #if (nskim > 0):
    #    print('buffer cleared of ',nskim, 'bytes\n')
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
        if leni > rxbuf:
            maxRxBuf(15000)
            print("Buffer Cleared")
            return((0,0,0,0))

        #print('3')
        else:
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
                #RFRaw.append(0)
                #chRaw.append(ch)
                countCal.append(count)
                towMsCal.append(towMsR)
                towSubMsCal.append(towSubMsR)
                return (wnoR, towMsR, towSubMsR, timeValid)
                #print('6')

            if det==0:
                return[
                    (0, 1, ch, wnoR, towMsR, towSubMsR),
                    (1, 1, ch, wnoF, towMsF, towSubMsF)
                ]
            
    return (0,0,0,0)
    '''
    except Exception:
        print("Error in readData")
        error_msg = (100, mac_id, 5, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
    '''



    

# ---------- Connecting to Server ----------



    

# ---------- Main Loop ----------
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
  # 5 seconds
#print("Running")

error_msg = (100, mac_id, 15, time.ticks_ms(), ip_last_byte, 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, error_msg)
s.send(packet)

NEvents = 0
deltaT = 0
NEvents2=0
T0=time.ticks_us()

array_count = 0

while True:
    if ota_in_progress:
        print("OTA in progress: closing gps data socket")
        try:
            s.close()
        except Exception as e:
            print("Socket close error:", e)
        time.sleep(1_000_000)  # effectively idle until reset

    print("1")

    try:
            # Ensure Wi-Fi stays connected
        if not wlan.isconnected():
            print("Wi-Fi disconnected. Reconnecting...")
            con_to_wifi(ssid, password)
        maxRxBuf(10000) #Make sure buffer isnt full before recieving
        try:
            #print('buffer size ',uart1.any(), 'bytes\n')
            #print('time(ms)',int(time.time_ns()))
            req = s.recv(20) #Dont need poller, can just check for socket activity on a not blocking socket
            #print('time(ms)',int(time.time_ns()))
            #print("Data recieved:", len(req))
            #print('buffer size ',uart1.any(), 'bytes\n')
            print("2")
        except OSError as e:
            if e.args[0] in [11, 110, 104]:  # EAGAIN, ETIMEDOUT, ECONNRESET
                # No data or connection lost
                print("No data")
                continue
            else:
                print("Socket error:", e)
                try:
                    s.close()
                except:
                    pass
                s = connect_socket(host, port)  # your reconnect function
                continue

        if req:
            try:
                inst, w_num, ms, sub_ms, event_num = ustruct.unpack(request_packet_format, req) #There might be an error here. What if multiple messages came in at the same time and I read them all at the same time? Will they be lost as ustruct may only evaluate the first little bit?
                print("3")
            except Exception as e:

                print("Error unpacking request:", e)
                error_msg = (100, mac_id, 12, 0, 0, 0, 0, 0, 0, 0)
                packet = data_packing(send_packet_format, error_msg)
                s.send(packet)
                continue

            if inst == 99:
                RFRaw=RFRaw[-50:]
                chRaw=chRaw[-50:]
                countRaw=countRaw[-50:]
                countCal=countCal[-5:]
                towMsRaw=towMsRaw[-50:]
                towMsCal=towMsCal[-5:]
                towSubMsRaw=towSubMsRaw[-50:]
                towSubMsCal=towSubMsCal[-5:]
                

                print("Processing GPS request...")
                print('buffer size ',uart1.any(), 'bytes\n')

                #time.sleep(0.1)
                timesOfInterest = request(w_num, ms, sub_ms)
                print("4")
                if timesOfInterest is None or len(timesOfInterest)==0:
                    msg = (99, mac_id, 0, 0, 0, 0, 0, 0, event_num, array_count)

                    packet = data_packing(send_packet_format, msg)
                    s.send(packet)
                    array_count+=1
                    wdt.feed()
                    continue
                
                print(timesOfInterest)

                print("7")
                for i in range(len(timesOfInterest)):
                    inst = 99           
                    ID = mac_id
                    RF = timesOfInterest[i][0]              
                    cal = timesOfInterest[i][1]               
                    ch = timesOfInterest[i][2]           
                    w_num = timesOfInterest[i][3]   
                    ms = timesOfInterest[i][4]      
                    sub_ms = timesOfInterest[i][5]
                    event_num = event_num #Unnecessary
                    count = array_count #timesOfInterest[i][6]
                    
                    msg = (inst, ID, RF, cal, ch, w_num, ms, sub_ms, event_num, count)

                    packet = data_packing(send_packet_format, msg)
                    print("5")
                    try:
                        s.send(packet) #Should I start checking wifi and socket are active before sending? It seems kind of pointless,
                                        #I would have to reconnect to them anyway if it I wasnt and w
                        array_count+=1
                        NEvents2+=1
                        wdt.feed()
                        print('buffer size ',uart1.any(), 'bytes\n')
                        print("data sent")
                        print("6")
                    except Exception as e:
                        print("Send error:", e)
                        error_msg = (100, mac_id, 13, 0, 0, 0, 0, 0, 0, 0)
                        packet = data_packing(send_packet_format, error_msg)
                        s = reconnect_socket(s)
                        s.send(packet)

                        break  # Exit inner loop

                length=len(towMsRaw)
                NEvents += length-2
                deltaT += (towMsRaw[length-2] - towMsRaw[0])*1000000+ int((towSubMsRaw[length-2] - towSubMsRaw[0])/1000)
                if NEvents > 1000:
                    T1=time.ticks_us()
                    Rate = (NEvents*1000000000/2)/deltaT
                    Rate2 = (NEvents2*1000000/2)/(T1-T0)
                    print('**************************************************************************Rate:',NEvents, deltaT,Rate)
                    print('**************************************************************************Rate2:',NEvents2, T1-T0,Rate2)
                    #Rate2=round(Rate2)
                    Rate = round(Rate)
                    Rate2 = round(Rate2*1000)
                    NEvents=NEvents2=deltaT=0
                    T0=T1
                    
                    msg = (99, mac_id, 19, Rate, Rate2, 0, 0, 0, 0, 0)
                    rate_packet = data_packing(send_packet_format, msg)
                    try:
                        #s.send(rate_packet)
                        wdt.feed()
                        print('buffer size ',uart1.any(), 'bytes\n')

                        print("data sent")
                    except Exception as e:
                        print("error in rate calc")
                        #s = reconnect_socket()
                        break  # Exit inner loop

    except Exception as e:
        print("Main loop exception:", e)
        error_msg = (100, mac_id, 14, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)
        print("Error sent")
        #clearRxBuf()
        #maxRxbuf()

        #time.sleep(1)
        #s = reconnect_socket(s)
        continue

        
        





