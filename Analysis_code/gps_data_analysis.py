import numpy as np
import matplotlib.pyplot as plt

def read_data(data_file):

    read_data = []
    with open(data_file, 'r') as f:
        next(f) #Skip label row
        
        for line in f:
            parts = line.strip().split(';')
            
            values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            if values[8]<1000000: #Ignore nonsense ns timestamps
                read_data.append(values)
        
    return read_data

def ch_grouper(DATA):
    '''
    This function splits the read data by channel number
    '''
    data = read_data(DATA)

    #Seperates data based on gps channel
    ch0_list = [tup for tup in data if tup[4]==0]
    ch1_list = [tup for tup in data if tup[4]==1]
    
    return ch0_list, ch1_list

def timestamp_ns(tup):
    """Combine ms and sub-ms into a single nanosecond timestamp"""
    return ((tup[6] * 1000000) + tup[7]) 

gps_daq_20251002_run1_cycle1 = read_data('C:/Users/aclark2/Desktop/ESP 32/GPS Data/Run20251008/gps_daq_20251008_run6_cycle2.txt')

esp_48_timestamps = []
for tup in gps_daq_20251002_run1_cycle1:
    if tup[1] == 48 and tup[2] == 0:
        esp_48_timestamps.append(timestamp_ns(tup))

esp_48_timestamps = np.array(esp_48_timestamps)
esp_48_timestamps_diffs = np.diff(esp_48_timestamps)

print(len(esp_48_timestamps_diffs))
print(np.sum(esp_48_timestamps_diffs<40000000))

print(np.median(esp_48_timestamps_diffs))
esp_48_range_list = [i for i in range(len(esp_48_timestamps_diffs))]
plt.scatter(esp_48_range_list, esp_48_timestamps_diffs)
plt.title(f"ESP 48 (gps_daq_20251002_run1_cycle1) \n Median = {np.median(esp_48_timestamps_diffs)} \n Mean = {np.mean(esp_48_timestamps_diffs)}")
plt.xlabel("Index")
plt.ylabel("Period (ns)")
plt.show()

esp_188_timestamps = []
esp_188_timestamps_index_run1 = []
index = -1
for tup in gps_daq_20251002_run1_cycle1:
    if tup[1] == 188 and tup[2] == 0 and tup[4] == 0 and tup[8] != index:
        esp_188_timestamps.append(timestamp_ns(tup))
        esp_188_timestamps_index_run1.append(tup[8])
        index = tup[8]

esp_188_timestamps = np.array(esp_188_timestamps)
esp_188_timestamps_diffs = np.diff(esp_188_timestamps)
inverse = 1000000000 / esp_188_timestamps_diffs

print(f'Esp 188 Period:{np.median(esp_188_timestamps_diffs)}')
plt.scatter(esp_188_timestamps_index_run1[:len(esp_188_timestamps_diffs)], esp_188_timestamps_diffs)
plt.title(f"ESP 188 (gps_daq_20251002_run2_cycle1) \n Median = {np.median(esp_188_timestamps_diffs)}")
plt.xlabel("Index")
plt.ylabel("Period (ns)")
plt.show()

esp_188_timestamps_range = [i for i in range(len(inverse))]
plt.scatter(esp_188_timestamps_range, inverse)
plt.title("ESP 188 (gps_daq_20251002_run1_cycle1)")
plt.xlabel("Index")
plt.ylabel("Timestamp (ns)")
plt.show()
"""
gps_daq_20251002_run2_cycle1 = read_data('C:/Users/aclark2/Desktop/ESP 32/GPS Data/gps_daq_20251003_run2_cycle1.txt')

esp_48_timestamps = []
for tup in gps_daq_20251002_run2_cycle1:
    if tup[1] == 48 and tup[2] == 0:
        esp_48_timestamps.append(timestamp_ns(tup))

esp_48_timestamps = np.array(esp_48_timestamps)
esp_48_timestamps_diffs = np.diff(esp_48_timestamps)

print(np.median(esp_48_timestamps_diffs))
esp_48_range_list = [i for i in range(len(esp_48_timestamps_diffs))]
plt.scatter(esp_48_range_list, esp_48_timestamps_diffs)
plt.title(f"ESP 48 (gps_daq_20251002_run2_cycle1) \n Median = {np.median(esp_48_timestamps_diffs)}")
plt.xlabel("Index")
plt.ylabel("Period (ns)")
plt.show()

esp_188_timestamps = []
esp_188_timestamps_index_run2 = []
index = -1
for tup in gps_daq_20251002_run2_cycle1:
    if tup[1] == 188 and tup[2] == 0 and tup[4] == 0 and tup[8] != index:
        esp_188_timestamps.append(timestamp_ns(tup))
        esp_188_timestamps_index_run2.append(tup[8])
        index = tup[8]

esp_188_timestamps = np.array(esp_188_timestamps)
esp_188_timestamps_diffs = np.diff(esp_188_timestamps)
print((esp_188_timestamps_index_run2))
print((esp_188_timestamps_diffs))

print(f'Esp 188 Period:{np.median(esp_188_timestamps_diffs)}')
plt.scatter(esp_188_timestamps_index_run2[:len(esp_188_timestamps_diffs)], esp_188_timestamps_diffs)
plt.title(f"ESP 188 (gps_daq_20251002_run2_cycle1) \n Median = {np.median(esp_188_timestamps_diffs)}")
plt.xlabel("Index")
plt.ylabel("Period (ns)")
plt.show()

esp_188_timestamps_range = [i for i in range(len(esp_188_timestamps))]
plt.scatter(esp_188_timestamps_range, esp_188_timestamps)
plt.title("ESP 188 (gps_daq_20251002_run2_cycle1)")
plt.xlabel("Index")
plt.ylabel("Timestamp (ns)")
plt.show()"""