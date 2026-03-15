#For run 13 
    #Det 8 has no wifi power saver and faster clock speed
    #Det 2 is normal
    #Measuring request time and total loop time

import numpy as np
import matplotlib.pyplot as plt
import os
from natsort import natsorted
from collections import defaultdict
from collections import Counter
import math

def ch_grouper(data): #Only risetimes
    '''
    This function splits the read data by channel number
    '''
    #Seperates data based on gps channel
    ch0_list = [tup for tup in data if tup[4]==0 and tup[2]==0]
    ch1_list = [tup for tup in data if tup[4]==1 and tup[2]==0]
    
    return ch0_list, ch1_list

def data_parser(file):
    if file.startswith("gps_daq"):
        file_path = os.path.join(folder_path, file)


        det1_rate = []
        det2_rate = []
        det3_rate = []
        det4_rate = []
        det5_rate = []
        det6_rate = []
        det7_rate = []
        det8_rate = []
        det9_rate = []
        det10_rate = []

        det2_rate98 = []
        det8_rate98 = []
        with open(file_path, 'r') as f:

            next(f) 
            for line in f:

                parts = line.strip().split(';')
                #print(parts)
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

                if values[0] == 95:  

 
                    if values[1]==180:
                        det2_rate.append(values)
                    if values[1]==20:
                        det8_rate.append(values) 

                
                if values[0] == 98:  

 
                    if values[1]==180:
                        det2_rate98.append(values)
                    if values[1]==20:
                        det8_rate98.append(values) 
        
            det2_rate = np.array(det2_rate) 
            det2_ur_reqs = det2_rate[:,3]
            det2_proc_time = det2_rate[:,4] / 1000
            det2_proc_time_mean = np.mean(det2_proc_time)
            det2_loop_time = det2_rate[:,5] /1000
            det2_loop_time_mean = np.mean(det2_loop_time)

            det8_rate = np.array(det8_rate) 
            det8_ur_reqs = det8_rate[:,3]
            det8_proc_time = det8_rate[:,4] / 1000
            det8_proc_time_mean = np.mean(det8_proc_time)
            det8_loop_time = det8_rate[:,5]/ 1000
            det8_loop_time_mean = np.mean(det8_loop_time)

            det2_rate98 = np.array(det2_rate98)
            det2_r_0 = (det2_rate98[:,2] / ((det2_rate98[:,4])/1000))
            det2_r_1 = (det2_rate98[:,3] / ((det2_rate98[:,4])/1000))

            det8_rate98 = np.array(det8_rate98)
            det8_r_0 = (det8_rate98[:,2] / (det8_rate98[:,4]/1000))
            det8_r_1 = (det8_rate98[:,3] / (det8_rate98[:,4]/1000))
                
            plt.plot(np.arange(len(det2_ur_reqs)), det2_ur_reqs, label = "Det 2 UR's")
            plt.plot(np.arange(len(det8_ur_reqs)), det8_ur_reqs, label = "Det 8 UR's")
            plt.legend()
            plt.ylabel("Frequency of Unreasonable Request Per 5s Interval")
            plt.xlabel("5s Interval")
            plt.title("Unreasonable Requests: Det 2 vs Det 8")
            plt.show()

            plt.plot(np.arange(len(det2_proc_time)), det2_proc_time, label = f"Det 2 Process Time \n Mean: {det2_proc_time_mean} ms")
            plt.plot(np.arange(len(det8_proc_time)), det8_proc_time, label = f"Det 8 Process Time \n Mean: {det8_proc_time_mean} ms")
            plt.legend()
            plt.ylabel("Process Time Per 5s Interval (ms)")
            plt.xlabel("5s Interval")
            plt.title("Process Time: Det 2 vs Det 8")
            plt.show()

            plt.plot(np.arange(len(det2_loop_time)), det2_loop_time, label = f"Det 2 Loop Time \n Mean: {det2_loop_time_mean} ms")
            plt.plot(np.arange(len(det8_loop_time)), det8_loop_time, label = f"Det 8 Loop Time \n Mean: {det8_loop_time_mean} ms")
            plt.legend()
            plt.ylabel("Loop Time Per 5s Interval (ms)")
            plt.xlabel("5s Interval")
            plt.title("Loop Time: Det 2 vs Det 8")
            plt.show()

            plt.plot(np.arange(len(det2_r_0)), det2_r_0, label = f"Det 2 Ch0 Rate \n Mean: {np.mean(det2_r_0):.2f} Hz")
            plt.plot(np.arange(len(det2_r_1)), det2_r_1, label = f"Det 2 Ch1 Rate \n Mean: {np.mean(det2_r_1):.2f} Hz")
            plt.plot(np.arange(len(det8_r_0)), det8_r_0, label = f"Det 8 Ch0 Rate \n Mean: {np.mean(det8_r_0):.2f} Hz")
            plt.plot(np.arange(len(det8_r_1)), det8_r_1, label = f"Det 8 Ch1 Rate \n Mean: {np.mean(det8_r_1):.2f} Hz")
            plt.legend()
            plt.xlabel("5s Interval")
            plt.ylabel("Rate (Hz)")
            plt.title("Channel Rates: Det 2 vs Det 8")
            plt.show()
if __name__ == "__main__":

    with open('det_data.txt', 'w') as f:
        f.close()

    folder_pre = "C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\GPS Data"
    run_num = "Run_0013_20260223"

    save_folder_path = 'C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\Graphs\\'
    save_folder = os.path.join(save_folder_path, run_num)

    os.makedirs(save_folder, exist_ok=True)  
    folder_path = os.path.join(folder_pre, run_num)

    file = 'gps_daq_20260223_run0013_cycle0002.txt'
    
    data_parser(file)
    
    #plotter(False)