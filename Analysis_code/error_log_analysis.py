import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from natsort import natsorted
import os


readdata_errors_list = defaultdict(list)

run_num = 'Run_0020_20260227'
data_folder_path = "C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\GPS Data"
data_folder = os.path.join(data_folder_path, run_num)

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

files_list = folder_reader(data_folder)
rate_list = defaultdict(list)

for file in files_list:
    
    with open(file, 'r') as f:

        next(f)
        
        for line in f:

            parts = line.strip().split(';')
            #print(parts)
            try:
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            except Exception as e:
                print("Error", e)
                continue

            if values[0] == 98: # Error Code  

                detector_id = values[1]
                readdata_errors_list[detector_id].append(values[1]+values[2]/ (values[3/1000)]) 

error_file = "C:\\Users\\alexc\\Desktop\\KoForce GPS DAQ\\ESP 32\\GPS Data\\Run_0020_20260227\\error_log.txt"
readdata_errors_list = defaultdict(list)

with open(error_file, 'r') as f:

        for line in f:
            
            parts = line.strip().split(':')
            parts = parts[1].strip().split(';')

            try:
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            except Exception as e:
                print("Error", e)
                continue
            
            if values[0] == 100: # Error Code  

                if values[2]==6: # read data error

                    detector_id = values[1]
                    readdata_errors_list[detector_id].append(values) 

error_count_list=[len(val) for val in readdata_errors_list.values()]
#print(error_count_list)

for key,count in zip(readdata_errors_list.keys(), error_count_list):
    readdata_errors_list[key] = count

print(readdata_errors_list)

detector_id_dict= {1:112, 2:180, 3:172, 4:64, 5:216, 6:252, 7:224, 8:20, 9:104, 10:164}
effs = [0.9166769765588019, 0.9108196647088777, 0.9252492255483487, 0.8934082939729254, 0.9621803404503999, 0.9532307938619499, 0.9330807174467766, 0.9797245051076549, 0.917534287855269, 0.9429158595188495]

for key, val, effs in zip(detector_id_dict.keys(), detector_id_dict.values(),effs):

    plt.bar((key), readdata_errors_list[val], label = f'Data Integrity: {100*effs:.2f}%' )

plt.xlabel("Detector #")
plt.ylabel("Error Count")
plt.title("ReadData Errors Per Detector")
plt.legend()
plt.show()    
          