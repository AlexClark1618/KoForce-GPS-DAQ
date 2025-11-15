"""import numpy as np
import matplotlib.pyplot as plt

data = []
with open("8R Two Side Test.txt", 'r') as f:
    next(f)
    
    for line in f:
        parts = line.strip().split(';')

        values = tuple(int(p.strip()) for p in parts)

        data.append(values)

print("Length of data:" , len(data))

rise_list= []
for tup in data:
    temp_list = []
    if tup[1] == 48 and tup[2] == 1:
        temp_list.append(tup)

        for tup1 in data:

            if tup1[1] == 200 and tup1[2] == 1 and abs(tup[6] - tup1[6])<0.5:
                temp_list.append(tup1)
    if len(temp_list)>1:
        rise_list.append(temp_list)
        
fall_list= []
for tup in data:
    temp_list = []
    if tup[1] == 48 and tup[2] == 0:
        temp_list.append(tup)

        for tup1 in data:

            if tup1[1] == 200 and tup1[2] == 0 and tup[6] == tup1[6]:
                temp_list.append(tup1)
    if len(temp_list)>1:
        fall_list.append(temp_list)

print("Length of rise list:", len(rise_list))
print("Length of fall list:", len(fall_list))

rise_time_diffs = []
count = 0
for pair in rise_list:

    time_diff = pair[1][7] - pair[0][7]

    rise_time_diffs.append(time_diff)

    if time_diff>10:
        count+=1
print(count)

print(rise_time_diffs)

fall_time_diffs = []
for pair in fall_list:

    time_diff = pair[1][7] - pair[0][7]

    if time_diff<1000000:
        fall_time_diffs.append(time_diff)           

print(fall_time_diffs)

#plt.hist(rise_time_diffs)

plt.hist(fall_time_diffs)
plt.show()"""

import matplotlib.pyplot as plt

# ---------- Load data ----------
data48 = []
data200 = []

with open("8R Two Side Test.txt", "r") as f:
    next(f)
    for line in f:
        # skip empty lines
        if not line.strip():
            continue
        
        parts = line.strip().split(";")
        
        # try to parse as integers, skip if it's header text
        try:
            values = [int(p.strip()) for p in parts]
        except ValueError:
            continue  # this skips the header line
        
        ID = values[1]
        ms = values[6]
        ns = values[7]
        time_ns = ms * 1_000_000 + ns

        if ID == 48:
            data48.append(time_ns)
        elif ID == 200:
            data200.append(time_ns)

# ---------- Match coincidences ----------
time_diffs = []
j = 0
for t in data48:
    # advance j until df200[j] is closest to t
    while j+1 < len(data200) and abs(data200[j+1] - t) < abs(data200[j] - t):
        j += 1
    time_diffs.append(data200[j] - t)

# ---------- Plot histogram ----------
plt.hist(time_diffs, bins=100)
plt.xlabel("Time difference (ns) (ID200 - ID48)")
plt.ylabel("Counts")
plt.title("Coincidence timing between ID 48 and ID 200")
plt.show()