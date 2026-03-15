import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict


file_path = "C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\GPS Data\\Run_0020_20260227\\gps_daq_20260227_run0020_cycle0001.txt"

det8_ur = []

det1_rate96 = []
det2_rate96 = []
det3_rate96 = []
det4_rate96 = []
det5_rate96 = []
det6_rate96 = []
det7_rate96 = []
det8_rate96 = []
det9_rate96 = []
det10_rate96 = []

det1_rate97 = []
det2_rate97 = []
det3_rate97 = []
det4_rate97 = []
det5_rate97 = []
det6_rate97 = []
det7_rate97 = []
det8_rate97 = []
det9_rate97 = []
det10_rate97 = []

proc_time_data = defaultdict(list)
transit_time_data = defaultdict(list)

with open(file_path, 'r') as f:

        next(f) 
        for line in f:

            parts = line.strip().split(';')
            #print(parts)
            try:
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            except Exception as e:
                print("Error", e)
                continue
            
            if values[0] == 93:  

                if values[1]==20 and values[8]<0:
                    det8_ur.append(values) 
          

            if values[0] == 96:  

                detector_id = values[1]
                proc_time_data[detector_id].append(values[2:6])

            if values[0] == 97 and values[1]!=48 and values[1]!=16:  

                detector_id = values[1]
                transit_time_data[detector_id].append(values[2:9])


#Code 96- Proc Time

for det_id in sorted(proc_time_data):
    if det_id == 20 or det_id == 180:

        array = np.array(proc_time_data[det_id])
        plt.plot(array[:,0], label="Avg Proc Time")
        plt.plot(array[:,1], label="Max Proc Time")

        plt.title(f"Average Vs Maximum Processing Time For Detector ID {det_id}")
        plt.xlabel("5s Interval")
        plt.ylabel("Time (us)")
        plt.legend()
        #plt.show()
plt.clf()    

for det_id in sorted(proc_time_data):
    if det_id == 20 or det_id == 180:

        array = np.array(proc_time_data[det_id])

        plt.plot(array[:,2], label="Avg Loop Time")
        plt.plot(array[:,3], label="Max Loop Time")

        plt.title(f"Average Vs Maximum Loop Time For Detector ID {det_id}")
        plt.xlabel("5s Interval")
        plt.ylabel("Time (us)")
        plt.legend()
plt.clf()    

        #plt.show()
#Code 97- Transit Time

print(transit_time_data.keys())
for det_id in sorted(transit_time_data):
    if det_id == 20 or det_id == 180:
        array = np.array(transit_time_data[det_id])

        plt.plot(array[:,0], label="Avg Transit Time")
        plt.plot(array[:,1], label="Min Transit Time")
        plt.plot(array[:,2], label="Max Tranist Time")


        plt.title(f"Tranist Time for Detector ID {det_id}")
        plt.xlabel("5s Interval")
        plt.ylabel("Time (ms)")
        plt.legend()

        plt.show()
plt.clf()    

for det_id in sorted(transit_time_data):
    if det_id == 20 or det_id == 180:
        array = np.array(transit_time_data[det_id])

        plt.plot(array[:,3], label="Avg Req Bunching")
        plt.plot(array[:,4], label="Max Bunching")
        plt.plot(array[:,5], label="Unreasonable Request Count")


        plt.title(f"Req Bunching vs Unreasonable Request Count Detector ID {det_id}")
        plt.xlabel("5s Interval")
        plt.ylabel("Counts")
        plt.legend()

        plt.show()
plt.clf()    
det8_ur_array = np.array(det8_ur)

req_diff = det8_ur_array[:,7]
print("Total UR:", len(req_diff))
req_diff = req_diff[req_diff<50000000]
req_diff_less_than_50 = req_diff[abs(req_diff)<50]
print("Number of UR with Delta T between 0 and 50ms:", sum(1 for tup in req_diff_less_than_50 if tup>0))
print("Number of UR with positive Delta T:", sum(1 for tup in req_diff if tup>0))

print("Number of UR with negative Delta T:",sum(1 for tup in req_diff if tup<0))

print(f"Percentage of UR with Delta T's in +-50ms window: {(len(req_diff_less_than_50)/len(req_diff))*100:.2f}")
#print(max(req_diff))
plt.hist(req_diff, bins=200)
#plt.xlim(-500,500)
plt.xlabel("DeltaT (ms)")

plt.title("Unreasonable Requests: DeltaT from Previous Request")
#plt.yscale('log')
plt.show()

req_diff = det8_ur_array[:,6]
print(np.mean(req_diff))

plt.hist(req_diff, bins=100)
#plt.xlim(-1000,1000)
#plt.yscale('log')
plt.xlabel("Transit Time (ms)")
plt.title("Unreasonable Requests: Tranist Time")

plt.show()

