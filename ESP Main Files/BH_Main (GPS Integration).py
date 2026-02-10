#Borehole

#Updated- 11/13/25 (Alex)

#Changelog:
    #General cleanup
    #More info packets
    #Improved send function to handle errors
    #Added timeout for send

import socket
import ustruct
import time
import network
from machine import UART, Pin, WDT
import time
import gc

#---------GPS Functions-----------
RXM_TM =(2,116)   #b'\x02\x74'
TIM_TM2= (13,3)   #b'\x0d\x03'
NAV_CLOCK= (1,34)       #b'\x01\x22'
POLL_NAV_CLOCK = b'\xb5\x62\x01\x22\x00\x00\x23\x6a'

uart1_tx_pin = 12  # Example: GPIO12
uart1_rx_pin = 14  # Example: GPIO14
rxbuf=8192*2
uart1 = UART(1, baudrate=115200*4, tx=Pin(uart1_tx_pin), rx=Pin(uart1_rx_pin), rxbuf=rxbuf)
uart1.write(POLL_NAV_CLOCK) #Poll Nav Clock

time.sleep(0.1)
numMeas=1
# ---------- Wifi and Socket Stuff ----------
def con_to_wifi(ssid, password):
    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(0.1)
    
    while not wlan.isconnected():
        try:
            print("Connecting to Wi-Fi...")
            wlan.connect(ssid, password)
            while not wlan.isconnected():
                time.sleep(1)
            print("Wi-Fi connected.")
            return wlan.ifconfig()
        except OSError as e:
            print(f"Connection attempt failed: {e}")
            
send_packet_format = "!iiiiiiiiii"

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

def connect_socket(host, port):
    while True:
        try:
            s = socket.socket()
            s.connect((host, port))
            print("Socket connected.")
            return s
        except Exception as e:
            print("Failed to connect socket:", e)
            time.sleep(1)

# ---------- GPS Functions ----------
def clearRxBuf():
    print('clearRxBuf')
    nTry=0
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    try:
        #print('clearRxBuf:', uart1.any(),'bytes')
        while uart1.any() and nTry < 4:
            print('buffer cleared of ',uart1.any(), 'bytes\n')
            (uart1.read())
            nTry += 1
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[];
        towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print("clearRxBuffer error:",e)
        print(uart1.any())
        uart1.read(1)
        uart1.read()
        #error_msg = (100, mac_id, 1, 0, 0, 0, 0, 0, 0)
        #packet = data_packing(send_packet_format, error_msg)
        #s.send(packet)
        pass

def maxRxBuf(n):
    print("maxRxBuf")
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal
    nTry = 0
    #print('maxRxBuf')
    try:
        while (uart1.any() > (n )) and nTry < 4:
            nskim = uart1.any()-n + 1000
            print('buffer cleared of ',nskim, 'bytes\n')
            (uart1.read(nskim))
            nTry += 1
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[];
        towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
    except Exception as e:
        print('maxRxbuf exception',e)
        error_msg = (100, mac_id, 2, 0, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        s.send(packet)

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

hdr2 = bytearray(4)
def findHDR2():
    while uart1.any() < 4:
        time.sleep_ms(1)
    uart1.readinto(hdr2)
    cls  = hdr2[0]
    msg  = hdr2[1]
    leni = hdr2[2] | (hdr2[3] << 8)
#    print('HDR2', cls,msg,leni)
    return cls, msg, leni

plb = bytearray(2048)
ck  = bytearray(2)

def readData():
    #print('readData')
    global slope
    global RFRaw, chRaw, countRaw, countCal, towMsRaw, towMsCal,towSubMsRaw, towSubMsCal


    try:
        # Find UBX sync
        findUBX_HDR()

        cls, msg, leni = findHDR2()
        if leni > 2048:
            #print("leni > 2048" )
            return (0, 0, 0, 0, 0)

        # Wait cooperatively for payload + checksum
        needed = leni + 2
        while uart1.any() < needed:
            time.sleep_ms(1)

        # Read payload + checksum without allocating
        uart1.readinto(plb, leni)
        uart1.readinto(ck, 2)

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

                RFRaw.append(RF)
                #print('RF',RFRaw,RF)
                chRaw.append(ch)
                #print('ch',chRaw,ch)
                countRaw.append(count)
                #print('count',countRaw,count)
                towMsRaw.append(towMs)
                towSubMsRaw.append(towSubMs)

                base += 24

        # ---------- TIM-TM2 ----------
        elif (cls, msg) == TIM_TM2:
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

            #if det == 1:
            countCal.append(count)
            towMsCal.append(towMsR)
            towSubMsCal.append(towSubMsR)
            return (wnoR, towMsR, towSubMsR, timeValid, ch)

#             return [
#                 (0, 1, ch, wnoR, towMsR, towSubMsR),
#                 (1, 1, ch, wnoF, towMsF, towSubMsF)
#             ]

        # ---------- NAV-CLOCK ----------
        elif (cls, msg) == NAV_CLOCK:
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
            #print('** slope =', slope)

        # Yield once after heavy UART work
        time.sleep_ms(0)
        return (0, 0, 0, 0, 0)

    except Exception as e:
        print("Error in readData:", e)
        return (0, 0, 0, 0, 0)


# ---------- Wi-Fi Setup ---------
ssid = 'AirShower2.4G'
password = 'Air$shower24'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

con_to_wifi(ssid, password)
full_mac = wlan.config('mac')
mac_id = wlan.config('mac')[-1]  # last byte of MAC
print("Mac ID:",mac_id)
ip, subnet, gateway, dns = wlan.ifconfig()
ip_last_byte = int(ip.split('.')[-1])          
print("ESP IP:", ip_last_byte)

# ---------- Connecting to Server ----------
#HOST = '192.168.0.93' #Home
#HOST = '134.69.200.155'
HOST = '134.69.77.61' #Karbon Computer
PORT = 12345

s = connect_socket(HOST,PORT)
#s.settimeout(.1)
s.setblocking(False)

# ---------- Send and Recieve Functions ----------
def send_data(d):
    global s
    
    try:
        return s.send(d)
        

    except OSError as e:
        if e.args[0] in [11, 110]:  # EAGAIN, ETIMEDOUT, ECONNRESET
            # No data or connection lost
            print("No data")
            
        else:
            print("Socket error:", e)
            try:
                s.close()
            except:
                pass
            s = connect_socket(HOST, PORT)  # your reconnect function
            
def recieve(num_bytes):
    global s
    try:

        data = s.recv(num_bytes) 

        if data:
            print("Wifi RX buffer cleared of:", len(data), "bytes")

    except OSError as e:
        if e.args[0] in [11, 110]:  # EAGAIN, ETIMEDOUT, ECONNRESET
            # No data or connection lost
            print("No data to clear")
            
        else:
            print("Socket error:", e)
            try:
                s.close()
            except:
                pass
            s = connect_socket(HOST, PORT)  # your reconnect function
            
# ---------- Info Packets ----------
error_msg = (100, mac_id, ip_last_byte, 15, time.ticks_ms(), 0, 0, 0, 0, 0) # This tells me when the board restarted how long it took to reach the main loop since booting
packet = data_packing(send_packet_format, error_msg)
send_data(packet)

time.sleep(0.1)

info_msg = (1, mac_id, ip_last_byte, 0, 0, 0, 0, 0, 0, 0) #Info Packet
packet = data_packing(send_packet_format, info_msg)
send_data(packet)

# ---------- Main Loop ----------

slope=0
tRaw1=None
Valid = 0
RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[];
towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]

while ((slope == 0) or (tRaw1 == None) or (Valid == 0)):
    print('\ninit while loop', slope, tRaw1, Valid)
    uart1.write(POLL_NAV_CLOCK) #Poll Nav Clock
    for i in range(4):
        res=readData()
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

T0=time.ticks_us()
event_num = 0 #Keeps track of borehole events (could be moved to server)

wdt = WDT(timeout=20000)  # 5 seconds

send_buffer = bytearray()

while True:
    try:
        #Checks for wifi disconnections. (May want to move this to an exception handle)
        if not wlan.isconnected():
            con_to_wifi(ssid, password)
        
        maxRxBuf(15000) #Make sure buffer isnt full before recieving      
        res = (0,0,0)
        RFRaw=[]; chRaw=[]; countRaw=[]; countCal=[]; towMsRaw=[]; towMsCal=[]; towSubMsRaw=[]; towSubMsCal=[]
        toi = []
        T1=time.ticks_us()
        diff = time.ticks_diff(T1, T0)
        #Every 5 seconds poll Nav Clock
        if diff > 5_000_000:
            #print('NEvents')
            uart1.write(POLL_NAV_CLOCK)
            T0=T1

        while (res[0] == 0) or (res[4] == 1):
            res = readData()
            #print('res:', res)
        timeValid = res[3]
        wnoToi=res[0]
        lastC=len(countCal)-1
        lastR=len(countRaw)-1

        for i in range(lastR,-1,-1):
            if countRaw[i]==countCal[lastC]:
                tCal1=towMsCal[lastC]*1000000+(towSubMsCal[lastC])
                tRaw1=towMsRaw[i]*1000000+ towSubMsRaw[i]//1000
                break

        lenRaw=len(towMsRaw)
        for i in range(lenRaw):   #
            if chRaw[i] == 0:
                tRaw=towMsRaw[i]*1000000+ towSubMsRaw[i]//1000           
                res=(tRaw-tRaw1)-((tRaw-tRaw1)*slope//1000000000)+tCal1
                Ms=res//1000000
                SubMs = res - Ms * 1000000
                toi.append((RFRaw[i],timeValid,chRaw[i],wnoToi,Ms,SubMs, countRaw[i], i)) 
        for i in range(len(toi)): #Select among the channel 0
            #print("i",i,end=" ")
            if toi[i][0] == 0:  #if it is a rise
                #print("R",end=" ")
                iRaw=toi[i][7]# pointing to raw data with ch0, rise
                tRaw= towMsRaw[iRaw]*1_000_000 + towSubMsRaw[iRaw]//1000  # raw time for ch0, rise
                for j in range(lenRaw):
                    #print("j",j,end=" ")
                    if chRaw[j] == 1:  #select encoding
                        #print("C1",end=" ")
                        tRaw2 = towMsRaw[j]*1_000_000 + towSubMsRaw[j]//1000  # raw time for ch1, rise or fall
                        diff = tRaw2-tRaw #tEncoding - tSignal
                        #print("D",diff,end=" ")
                        if (diff < 750)  and (diff >= 0):  #encoding of interest within 500 ns of rise of ch0
                            #print("Y",end=" ")
                            res=(tRaw2-tRaw1)-((tRaw2-tRaw1)*slope//1000000000)+tCal1  #Cal encoding time
                            Ms=res//1000000
                            SubMs = res - Ms * 1000000
                            #append encoding of interest, use same count as ch0
                            toi.append((RFRaw[j],timeValid,1,wnoToi,Ms,SubMs,countRaw[iRaw], j))        
        
        ID=mac_id
        
        for i in range(len(toi)):
            inst = 99           
            ID = mac_id
            RF = toi[i][0]              
            cal = toi[i][1]               
            ch = toi[i][2]           
            w_num = toi[i][3]   
            ms = toi[i][4]      
            sub_ms = toi[i][5]
            event_num = event_num 
            count = toi[i][6] 

            msg = (inst, ID, RF, cal, ch, w_num, ms, sub_ms, event_num, count)
            
            packet = data_packing(send_packet_format, msg)

            send_buffer+=packet

        try:
            data = send_data(send_buffer)
            if data: 
                print("!!!!!!!!!!!!!!!!!!!!!data sent", len(send_buffer) )
            send_buffer = bytearray()
            recieve(1024) #Keeps socket empty
            wdt.feed()
            event_num +=1 
        except Exception as e:
            print("Send error:", e)
            continue

    except Exception as e:
        print("Error in main loop", e)
        error_msg = (100, mac_id, ip_last_byte, 14, 0, 0, 0, 0, 0, 0)
        packet = data_packing(send_packet_format, error_msg)
        send_data(packet)
        continue
        
    
    

    


