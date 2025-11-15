import numpy as np
import matplotlib.pyplot as plt
import os
from natsort import natsorted
from collections import defaultdict
from collections import Counter


#What do I want this code to do:
    #Period
    #Time over threshold
    #Coincidences with the borehole
folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\Run 26'

def folder_reader(folder_path): 
    folder_files_list = []     
    for filename in os.listdir(folder_path):
        if filename.startswith('gps_daq'):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):  # make sure it's a file
                file_name = file_path.replace("\\", "/")
                folder_files_list.append(file_name)
    return natsorted(folder_files_list) #Correctly sorted them based on number

def file_joiner():
    """
    Combines all files from a folder into a single txt file
    """
    folder_files_list= folder_reader(folder_path)
    #print(folder_files_list)
    
    with open('joined_file.txt','w') as outfile:

        for file in folder_files_list:
            with open(file, 'r') as infile:
                next(infile)

                for line in infile:
                    outfile.write(line)
    outfile.close()
    
    print("File joiner complete")
    return None

file_joiner() #Call file joiner function

def ch_grouper(data):
    '''
    This function splits the read data by channel number
    '''
    #Seperates data based on gps channel
    ch0_list = [tup for tup in data if tup[4]==0]
    ch1_list = [tup for tup in data if tup[4]==1]
    
    return ch0_list, ch1_list

def timestamp_ns(tup):
    """Combine ms and sub-ms into a single nanosecond timestamp"""
    return ((tup[6] * 1000000) + tup[7]) 

DATA_FILE = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\joined_file.txt' #Automatically use joined file

BH_list = []
det1_list = []
det2_list = []
det3_list = []
det4_list = []
det5_list = []
det6_list = []
det7_list = []
det8_list = []
det9_list = []
det10_list = []
all_data = []

def read_data(data_file):

    with open(data_file, 'r') as f:
        
        for line in f:
            if line.startswith('[ESP]'): #Deals with the stupid marker in run 17
                continue
            
            if line.startswith('Unknown Code'):
                continue

            parts = line.strip().split(';')
            #print(parts)
            values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            if values[0]==99 and values[5]!=0: #Real data
                if values[6]<604800000 and values[7]<1000000: #Ignore nonsense ms and ns timestamps
                    all_data.append(values)

                    if values[1]==48:
                        BH_list.append(values)
                    if values[1]==112:
                        det1_list.append(values)
                    if values[1]==180:
                        det2_list.append(values)
                    if values[1]==172:
                        det3_list.append(values)
                    if values[1]==64:
                        det4_list.append(values)
                    if values[1]==232:
                        det5_list.append(values)
                    if values[1]==252:
                        det6_list.append(values)
                    if values[1]==224:
                        det7_list.append(values)
                    if values[1]==188:
                        det8_list.append(values)
                    if values[1]==104:
                        det9_list.append(values)
                    if values[1]==164:
                        det10_list.append(values)
        
    print("Read data complete") 

read_data(DATA_FILE) #Call read data with joined file 

def period_calculator(det):
    #Should do both channels
    if det == 'BH':
        BH_ch0, BH_ch1 = ch_grouper(BH_list)

        BH_ch0_timestamps = np.array([timestamp_ns(tup) for tup in BH_ch0 if tup[2]==0]) #Only Risetimes
        BH_ch0_period = np.diff(BH_ch0_timestamps)
        BH_ch0_period_mean = np.mean(BH_ch0_period)
        BH_ch0_period_median = np.median(BH_ch0_period)
        BH_ch0_period_std = np.std(BH_ch0_period)

        BH_ch1_timestamps = np.array([timestamp_ns(tup) for tup in BH_ch1 if tup[2]==0])
        BH_ch1_period = np.diff(BH_ch1_timestamps)
        BH_ch1_period_mean = np.mean(BH_ch1_period)
        BH_ch1_period_median = np.median(BH_ch1_period)
        BH_ch1_period_std = np.std(BH_ch1_period)

        BH_period_packet = [(BH_ch0_period, BH_ch0_period_mean, BH_ch0_period_median, BH_ch0_period_std),
                            (BH_ch1_period, BH_ch1_period_mean, BH_ch1_period_median, BH_ch1_period_std)]

    #Fix others to be like above 
    if det == 1:
        det1_timestamps = np.array([timestamp_ns(tup) for tup in det1_list])
        det1_period = np.diff(det1_timestamps)
        det1_period_mean = np.mean(det1_period)
        det1_period_median = np.median(det1_period)
        det1_period_std = np.std(det1_period)

        det1_period_packet = [det1_period, det1_period_mean, det1_period_median, det1_period_std]

    if det == 2:
        det2_timestamps = np.array([timestamp_ns(tup) for tup in det2_list])
        det2_period = np.diff(det2_timestamps)
        det2_period_mean = np.mean(det2_period)
        det2_period_median = np.median(det2_period)
        det2_period_std = np.std(det2_period)

        det2_period_packet = [det2_period, det2_period_mean, det2_period_median, det2_period_std]

    if det == 3:
        det3_timestamps = np.array([timestamp_ns(tup) for tup in det3_list])
        det3_period = np.diff(det3_timestamps)
        det3_period_mean = np.mean(det3_period)
        det3_period_median = np.median(det3_period)
        det3_period_std = np.std(det3_period)

        det3_period_packet = [det3_period, det3_period_mean, det3_period_median, det3_period_std]

    if det ==4: 
        det4_timestamps = np.array([timestamp_ns(tup) for tup in det4_list])
        det4_period = np.diff(det4_timestamps)
        det4_period_mean = np.mean(det4_period)
        det4_period_median = np.median(det4_period)
        det4_period_std = np.std(det4_period)

        det4_period_packet = [det4_period, det4_period_mean, det4_period_median, det4_period_std]   

    if det ==5:
        det5_timestamps = np.array([timestamp_ns(tup) for tup in det5_list])
        det5_period = np.diff(det5_timestamps)
        det5_period_mean = np.mean(det5_period)
        det5_period_median = np.median(det5_period)
        det5_period_std = np.std(det5_period)

        det5_period_packet = [det5_period, det5_period_mean, det5_period_median, det5_period_std]

    if det == 6:
        det6_timestamps = np.array([timestamp_ns(tup) for tup in det6_list])
        det6_period = np.diff(det6_timestamps)
        det6_period_mean = np.mean(det6_period)
        det6_period_median = np.median(det6_period)
        det6_period_std = np.std(det6_period)

        det6_period_packet = [det6_period, det6_period_mean, det6_period_median, det6_period_std]

    if det == 7:
        det7_timestamps = np.array([timestamp_ns(tup) for tup in det7_list])
        det7_period = np.diff(det7_timestamps)
        det7_period_mean = np.mean(det7_period)
        det7_period_median = np.median(det7_period)
        det7_period_std = np.std(det7_period)

        det7_period_packet = [det7_period, det7_period_mean, det7_period_median, det7_period_std]

    if det == 8:
        det8_timestamps = np.array([timestamp_ns(tup) for tup in det8_list])
        det8_period = np.diff(det8_timestamps)
        det8_period_mean = np.mean(det8_period)
        det8_period_median = np.median(det8_period)
        det8_period_std = np.std(det8_period)

        det8_period_packet = [det8_period, det8_period_mean, det8_period_median, det8_period_std]

    if det == 9:
        det9_timestamps = np.array([timestamp_ns(tup) for tup in det9_list])
        det9_period = np.diff(det9_timestamps)
        det9_period_mean = np.mean(det9_period)
        det9_period_median = np.median(det9_period)
        det9_period_std = np.std(det9_period)

        det9_period_packet = [det9_period, det9_period_mean, det9_period_median, det9_period_std]

    if det == 10:
        det10_timestamps = np.array([timestamp_ns(tup) for tup in det10_list])
        det10_period = np.diff(det10_timestamps)
        det10_period_mean = np.mean(det10_period)
        det10_period_median = np.median(det10_period)
        det10_period_std = np.std(det10_period)

        det10_period_packet = [det10_period, det10_period_mean, det10_period_median, det10_period_std]

    return BH_period_packet, det1_period_packet, det2_period_packet, det3_period_packet, det4_period_packet, det5_period_packet, det6_period_packet, det7_period_packet, det8_period_packet, det9_period_packet, det10_period_packet

def period_plotter():

    ###det2###
    #det2_period_packet = [(det2_ch0_period, det2_ch0_period_mean, det2_ch0_period_median, det2_ch0_period_std),
    #                    (det2_ch1_period, det2_ch1_period_mean, det2_ch1_period_median, det2_ch1_period_std)]

    #Ch0
    #plt.hist(,det2_period_packet[0][0])
    return
    #Ch1
def time_over_thres():

    ###BH###
    BH_ch0, BH_ch1 = ch_grouper(BH_list)
    BH_ch0_timestamps = np.array([timestamp_ns(tup) for tup in BH_ch0]) 
    BH_ch1_timestamps = np.array([timestamp_ns(tup) for tup in BH_ch1])

    BH_ch0_tot = np.diff(BH_ch0_timestamps) 
    BH_ch0_tot = BH_ch0_tot[BH_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    BH_ch0_tot_mean = np.mean(BH_ch0_tot)
    BH_ch0_tot_std  = np.std(BH_ch0_tot)

    BH_ch1_tot = np.diff(BH_ch1_timestamps)
    BH_ch1_tot = BH_ch1_tot[BH_ch1_tot<10000]
    BH_ch1_tot_mean = np.mean(BH_ch1_tot)
    BH_ch1_tot_std  = np.std(BH_ch1_tot)

    BH_tot_packet = [(BH_ch0_tot, BH_ch0_tot_mean, BH_ch0_tot_std),
                     (BH_ch1_tot, BH_ch1_tot_mean, BH_ch1_tot_std)]

    ###Det1###
    det1_ch0, det1_ch1 = ch_grouper(det1_list)
    det1_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det1_ch0]) 
    det1_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det1_ch1])

    det1_ch0_tot = np.diff(det1_ch0_timestamps) 
    det1_ch0_tot = det1_ch0_tot[det1_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det1_ch0_tot_mean = np.mean(det1_ch0_tot)
    det1_ch0_tot_std  = np.std(det1_ch0_tot)

    det1_ch1_tot = np.diff(det1_ch1_timestamps)
    det1_ch1_tot = det1_ch1_tot[det1_ch1_tot<10000]
    det1_ch1_tot_mean = np.mean(det1_ch1_tot)
    det1_ch1_tot_std  = np.std(det1_ch1_tot)

    det1_tot_packet = [(det1_ch0_tot, det1_ch0_tot_mean, det1_ch0_tot_std),
                     (det1_ch1_tot, det1_ch1_tot_mean, det1_ch1_tot_std)]
    ###Det2###
    det2_ch0, det2_ch1 = ch_grouper(det2_list)
    det2_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det2_ch0]) #Only Risetimes
    det2_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det2_ch1])

    det2_ch0_tot = np.diff(det2_ch0_timestamps) 
    det2_ch0_tot = det2_ch0_tot[det2_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det2_ch0_tot_mean = np.mean(det2_ch0_tot)
    det2_ch0_tot_std  = np.std(det2_ch0_tot)

    det2_ch1_tot = np.diff(det2_ch1_timestamps)
    det2_ch1_tot = det2_ch1_tot[det2_ch1_tot<10000]
    det2_ch1_tot_mean = np.mean(det2_ch1_tot)
    det2_ch1_tot_std  = np.std(det2_ch1_tot)

    det2_tot_packet = [(det2_ch0_tot, det2_ch0_tot_mean, det2_ch0_tot_std),
                     (det2_ch1_tot, det2_ch1_tot_mean, det2_ch1_tot_std)]

    ###Det3###
    det3_ch0, det3_ch1 = ch_grouper(det3_list)
    det3_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det3_ch0]) #Only Risetimes
    det3_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det3_ch1])

    det3_ch0_tot = np.diff(det3_ch0_timestamps) 
    det3_ch0_tot = det3_ch0_tot[det3_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det3_ch0_tot_mean = np.mean(det3_ch0_tot)
    det3_ch0_tot_std  = np.std(det3_ch0_tot)

    det3_ch1_tot = np.diff(det3_ch1_timestamps)
    det3_ch1_tot = det3_ch1_tot[det3_ch1_tot<10000]
    det3_ch1_tot_mean = np.mean(det3_ch1_tot)
    det3_ch1_tot_std  = np.std(det3_ch1_tot)

    det3_tot_packet = [(det3_ch0_tot, det3_ch0_tot_mean, det3_ch0_tot_std),
                     (det3_ch1_tot, det3_ch1_tot_mean, det3_ch1_tot_std)]

    ###Det4###
    det4_ch0, det4_ch1 = ch_grouper(det4_list)
    det4_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det4_ch0]) #Only Risetimes
    det4_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det4_ch1])

    det4_ch0_tot = np.diff(det4_ch0_timestamps) 
    det4_ch0_tot = det4_ch0_tot[det4_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det4_ch0_tot_mean = np.mean(det4_ch0_tot)
    det4_ch0_tot_std  = np.std(det4_ch0_tot)

    det4_ch1_tot = np.diff(det4_ch1_timestamps)
    det4_ch1_tot = det4_ch1_tot[det4_ch1_tot<10000]
    det4_ch1_tot_mean = np.mean(det4_ch1_tot)
    det4_ch1_tot_std  = np.std(det4_ch1_tot)

    det4_tot_packet = [(det4_ch0_tot, det4_ch0_tot_mean, det4_ch0_tot_std),
                     (det4_ch1_tot, det4_ch1_tot_mean, det4_ch1_tot_std)]

    ###Det5###
    det5_ch0, det5_ch1 = ch_grouper(det5_list)
    det5_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det5_ch0]) #Only Risetimes
    det5_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det5_ch1])

    det5_ch0_tot = np.diff(det5_ch0_timestamps) 
    det5_ch0_tot = det5_ch0_tot[det5_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det5_ch0_tot_mean = np.mean(det5_ch0_tot)
    det5_ch0_tot_std  = np.std(det5_ch0_tot)

    det5_ch1_tot = np.diff(det5_ch1_timestamps)
    det5_ch1_tot = det5_ch1_tot[det5_ch1_tot<10000]
    det5_ch1_tot_mean = np.mean(det5_ch1_tot)
    det5_ch1_tot_std  = np.std(det5_ch1_tot)

    det5_tot_packet = [(det5_ch0_tot, det5_ch0_tot_mean, det5_ch0_tot_std),
                     (det5_ch1_tot, det5_ch1_tot_mean, det5_ch1_tot_std)]

    ###Det6###
    det6_ch0, det6_ch1 = ch_grouper(det6_list)
    det6_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det6_ch0]) #Only Risetimes
    det6_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det6_ch1])

    det6_ch0_tot = np.diff(det6_ch0_timestamps) 
    det6_ch0_tot = det6_ch0_tot[det6_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det6_ch0_tot_mean = np.mean(det6_ch0_tot)
    det6_ch0_tot_std  = np.std(det6_ch0_tot)

    det6_ch1_tot = np.diff(det6_ch1_timestamps)
    det6_ch1_tot = det6_ch1_tot[det6_ch1_tot<10000]
    det6_ch1_tot_mean = np.mean(det6_ch1_tot)
    det6_ch1_tot_std  = np.std(det6_ch1_tot)

    det6_tot_packet = [(det6_ch0_tot, det6_ch0_tot_mean, det6_ch0_tot_std),
                     (det6_ch1_tot, det6_ch1_tot_mean, det6_ch1_tot_std)]

    ###Det7###
    det7_ch0, det7_ch1 = ch_grouper(det7_list)
    det7_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det7_ch0]) #Only Risetimes
    det7_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det7_ch1])

    det7_ch0_tot = np.diff(det7_ch0_timestamps) 
    det7_ch0_tot = det7_ch0_tot[det7_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det7_ch0_tot_mean = np.mean(det7_ch0_tot)
    det7_ch0_tot_std  = np.std(det7_ch0_tot)

    det7_ch1_tot = np.diff(det7_ch1_timestamps)
    det7_ch1_tot = det7_ch1_tot[det7_ch1_tot<10000]
    det7_ch1_tot_mean = np.mean(det7_ch1_tot)
    det7_ch1_tot_std  = np.std(det7_ch1_tot)

    det7_tot_packet = [(det7_ch0_tot, det7_ch0_tot_mean, det7_ch0_tot_std),
                     (det7_ch1_tot, det7_ch1_tot_mean, det7_ch1_tot_std)]

    ###Det8###
    det8_ch0, det8_ch1 = ch_grouper(det8_list)
    det8_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det8_ch0]) #Only Risetimes
    det8_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det8_ch1])

    det8_ch0_tot = np.diff(det8_ch0_timestamps) 
    det8_ch0_tot = det8_ch0_tot[det8_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det8_ch0_tot_mean = np.mean(det8_ch0_tot)
    det8_ch0_tot_std  = np.std(det8_ch0_tot)

    det8_ch1_tot = np.diff(det8_ch1_timestamps)
    det8_ch1_tot = det8_ch1_tot[det8_ch1_tot<10000]
    det8_ch1_tot_mean = np.mean(det8_ch1_tot)
    det8_ch1_tot_std  = np.std(det8_ch1_tot)

    det8_tot_packet = [(det8_ch0_tot, det8_ch0_tot_mean, det8_ch0_tot_std),
                     (det8_ch1_tot, det8_ch1_tot_mean, det8_ch1_tot_std)]

    ###Det9###
    det9_ch0, det9_ch1 = ch_grouper(det9_list)
    det9_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det9_ch0]) #Only Risetimes
    det9_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det9_ch1])

    det9_ch0_tot = np.diff(det9_ch0_timestamps) 
    det9_ch0_tot = det9_ch0_tot[det9_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det9_ch0_tot_mean = np.mean(det9_ch0_tot)
    det9_ch0_tot_std  = np.std(det9_ch0_tot)

    det9_ch1_tot = np.diff(det9_ch1_timestamps)
    det9_ch1_tot = det9_ch1_tot[det9_ch1_tot<10000]
    det9_ch1_tot_mean = np.mean(det9_ch1_tot)
    det9_ch1_tot_std  = np.std(det9_ch1_tot)

    det9_tot_packet = [(det9_ch0_tot, det9_ch0_tot_mean, det9_ch0_tot_std),
                     (det9_ch1_tot, det9_ch1_tot_mean, det9_ch1_tot_std)]

    ###Det10###
    det10_ch0, det10_ch1 = ch_grouper(det10_list)
    det10_ch0_timestamps = np.array([timestamp_ns(tup) for tup in det10_ch0]) #Only Risetimes
    det10_ch1_timestamps = np.array([timestamp_ns(tup) for tup in det10_ch1])

    det10_ch0_tot = np.diff(det10_ch0_timestamps) 
    det10_ch0_tot = det10_ch0_tot[det10_ch0_tot<10000]#Lets assume there is a scenario when a rise or fall is missing, thats why I put a liberal limit of 10us
    det10_ch0_tot_mean = np.mean(det10_ch0_tot)
    det10_ch0_tot_std  = np.std(det10_ch0_tot)

    det10_ch1_tot = np.diff(det10_ch1_timestamps)
    det10_ch1_tot = det10_ch1_tot[det10_ch1_tot<10000]
    det10_ch1_tot_mean = np.mean(det10_ch1_tot)
    det10_ch1_tot_std  = np.std(det10_ch1_tot)

    det10_tot_packet = [(det10_ch0_tot, det10_ch0_tot_mean, det10_ch0_tot_std),
                     (det10_ch1_tot, det10_ch1_tot_mean, det10_ch1_tot_std)]

    return BH_tot_packet, det1_tot_packet, det2_tot_packet, det3_tot_packet, det4_tot_packet, det5_tot_packet, det6_tot_packet, det7_tot_packet, det8_tot_packet, det9_tot_packet, det10_tot_packet

def tot_plotter():
    return

def coincidence_finder():

    ###Convert all data to nanosecond timestamps###
    ns_all_data=[]
    for tup in all_data:
        if tup[2]==0: #Only risetimes
            ns_all_data.append((tup[1],timestamp_ns(tup)))

    ns_all_data = np.array(ns_all_data)

    device_ids = ns_all_data[:, 0]
    timestamps = ns_all_data[:, 1]
    #print(device_ids)

    # --- Separate timestamps by device ---
    devices = defaultdict(list)
    for dev, ts in zip(device_ids, timestamps):
        devices[dev].append(ts)
    # Convert to sorted numpy arrays
    for dev in devices:
        devices[dev] = np.sort(np.array(devices[dev], dtype=int))
    #print(devices)

    # --- Coincidence detection ---
    target = 48        # ESP 48
    Δt = 1000       # Coincidence within 1us
    coincidences = []

    t48 = devices[target]
    #print(t48)
    for t in t48:
        involved = [target]
        for dev, ts in devices.items():
            if dev == target:
                continue
            # Find timestamps within [t - Δt, t + Δt]
            left = np.searchsorted(ts, t - Δt, side='left')
            right = np.searchsorted(ts, t + Δt, side='right')
            if right > left:
                #print(ts[left:right])
                involved.append(dev)
        if len(involved) >= 2:
            coincidences.append((t, involved))
    #print(coincidences[0])
    print(f"Found {len(coincidences)} coincidences with ≥4 devices")
    for t, devs in coincidences[:10]:
        print(f"t={t} -> devices={devs}")
    
    num_dets = [len(devs) for _, devs in coincidences]

    # Count occurrences
    counts = Counter(num_dets)
    print(counts)
    # Print summary
    coin = 0
    for num, freq in sorted(counts.items()):
        print(f"{num} devices: {freq} coincidences")
        if num >= 4:
            coin+=freq
    print(coin)
    print(coin/64)

    plt.bar(counts.keys(), counts.values())
    plt.title(f"GPS DAQ Coincidences\n Coincidence Rate Per Hour=~{coin/64}")
    plt.xlabel("Number of Detectors Involved in Coincidence Event")
    plt.ylabel("Frequency")

    plt.show()


#if __name__ == "__main__":
    #stuff
    ##folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\Run20251007'

    #file_joiner(folder_path) #Call file joiner function
    #read_data(DATA_FILE)

coincidence_finder()
