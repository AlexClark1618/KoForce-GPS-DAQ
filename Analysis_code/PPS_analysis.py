import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import os
from natsort import natsorted
from collections import defaultdict
from collections import Counter

#What do I want this code to do:
    #Period
    #Time over threshold
    #Coincidences with the borehole
    #Summary file

    #1/16/25:
    #Look at rates sent to data file
    #Split veto and BH coincidence events

    #2/10/26:
    #2ch time diff distribution per det
    #Include two channels in coincidence
    
def folder_reader(folder_path):
    global folder_files_list 
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
    #global folder_path
    
    #print(folder_files_list)
    
    with open('joined_file.txt','w') as outfile:

        for i in range(0, len(folder_files_list),5):
        #for file in folder_files_list[:5]:
            file = folder_files_list[i]
            print(file)
            with open(file, 'r') as infile:
                next(infile)

                for line in infile:
                    outfile.write(line)
                
    outfile.close()
    
    print("File joiner complete")
    return None

def timestamp_sec(tup):
    """Combine ms and sub-ms into a single nanosecond timestamp"""
    return ((tup[5] * 604800 + tup[6] // 1000)) #+ tup[7]) 

bh_dict = defaultdict(list)
veto_dict = defaultdict(list)
det20_list = []
det164_list = []
det180_list = []


BH_list = []
Veto_list = []
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

start = (99, 48, 0, 1, 0, 2407, 513880598, 774430, 1, 50858)

def read_data(data_file, single_file):

    with open(data_file, 'r') as f:
        if single_file:
            next(f)

        unique_esp_macs = []

        for line in f:

            parts = line.strip().split(';')
            #print(parts)
            values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            if values[1]==48 and values[2] == 0 and values[4] ==0 and values[6]!=0: #Real dat

                bh_dict[values[8]].append(values)
            
            if values[1]==16 and values[2] == 0 and values[4] ==0 and values[6]!=0: #Real dat

                veto_dict[values[8]].append(values)
                        
            if values[1]==20 and values[0] == 98 : #Real dat

                det20_list.append(timestamp_sec(values)-timestamp_sec(start))

            if values[1]==164 and values[0] == 98 : #Real dat

                det164_list.append(timestamp_sec(values)-timestamp_sec(start))

            if values[1]==224 and values[0] == 98 : #Real dat

                det180_list.append(timestamp_sec(values)-timestamp_sec(start))
              
        #print(bh_dict.values())
    print("Read data complete") 
    
    return bh_dict, veto_dict, det20_list, det164_list, det180_list

sec_in_day = 86400
start = (99, 48, 0, 1, 0, 2407, 513880598, 774430, 1, 50858)
def pps_analysis():

    bh_dict, veto_dict, det20_list, det164_list, det180_list = read_data(DATA_FILE, False) #Call read data with joined file

    keys_list = bh_dict.keys()
    gps_list = bh_dict.values()
    #gps_array = np.array(gps_list)
    gps_hours = [((timestamp_sec(val[0])/3600) - timestamp_sec(start)/3600) for val in gps_list]
    #print(gps_hours)

    values_diff = [(timestamp_sec(val[1])- timestamp_sec(val[0])) for val in bh_dict.values()]
    values_diff = np.array(values_diff)

    plt.plot(gps_hours, values_diff/sec_in_day)
    plt.title(f"BH PPS - GPS Timestamp {run_num}")
    plt.xlabel("Hours from start of run")
    plt.ylabel("DeltaT (PPS-GPS) (Days)")
    #plt.show()

    keys_list = veto_dict.keys()
    gps_list = veto_dict.values()
    #print(gps_list)
    #gps_array = np.array(gps_list)
    gps_hours = [((timestamp_sec(val[1])/3600) - timestamp_sec(start)/3600) for val in gps_list]
    #print(gps_hours)

    values_diff = [(timestamp_sec(val[0])- timestamp_sec(val[1])) for val in veto_dict.values()]
    values_diff = np.array(values_diff)

    plt.plot(gps_hours, values_diff/sec_in_day)
    #plt.gca().invert_xaxis()
    plt.title(f"Veto PPS - GPS Timestamp {run_num}")
    plt.xlabel("Hours from start of run")
    plt.ylabel("DeltaT (PPS-GPS) (Days)")
    #plt.show() 
    
    plt.clf()
    det20_array = np.array(det20_list)
    plt.plot(np.arange(1, len(det20_list)+1), det20_array/sec_in_day)
    #plt.gca().invert_xaxis()
    plt.title(f"PPS Evolution Det 8 {run_num}")
    plt.xlabel("Run Progression")
    plt.ylabel("PPS - Start of Run (Days)")
    plt.show()  

    plt.clf()
    det164_array = np.array(det164_list)
    plt.plot(np.arange(1, len(det164_list)+1), det164_array/sec_in_day)
    #plt.gca().invert_xaxis()
    plt.title(f"PPS Evolution Det 10 {run_num}")
    plt.xlabel("Run Progression")
    plt.ylabel("PPS - Start of Run (Days)")
    plt.show()  

    plt.clf()
    det180_array = np.array(det180_list)
    plt.plot(np.arange(1, len(det180_list)+1), det180_array/sec_in_day)
    #plt.gca().invert_xaxis()
    plt.title(f"PPS Evolution Det 2 {run_num}")
    plt.xlabel("Run Progression")
    plt.ylabel("PPS - Start of Run (Days)")
    plt.show()  



if __name__ == "__main__":
    
    #Data Filter min & max
    min = 1
    max = 99
    
    #Run ID and folder paths
    run_num = 'Run_0020_20260227'

    save_folder_path = 'C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\Graphs\\'
    save_folder = os.path.join(save_folder_path, run_num)

    os.makedirs(save_folder, exist_ok=True)  


    data_folder_path = "C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\GPS Data"
    data_folder = os.path.join(data_folder_path, run_num)

    DATA_FILE = 'C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\joined_file.txt' #Automatically use joined file

    folder_files_list= folder_reader(data_folder)
    file_joiner()
    pps_analysis()

    

