import numpy as np
import matplotlib.pyplot as plt

data = []
with open("Asy_Cable_Len_Test.txt", 'r') as f:
    next(f)
    
    for line in f:
        parts = line.strip().split(';')

        values = tuple(int(p.strip()) for p in parts)

        data.append(values)


event_num = 0
group_list = []
for tup in data:
    
    temp_list = [tup for tup in data if tup[8]==event_num]
    event_num+=1

    if len(temp_list)>2:
        group_list.append(temp_list)

print(len(group_list))
time_diff_list=[]
event = 0
for event in group_list:

    if event[0][6] == event[2][6]:
        #print(event)
        #print(event[0][6])
        #print(event[2][6])
        #print(event[0][7])
        #print(event[2][7])
        time_diff_list.append(event[2][7]-event[0][7])

print(len(time_diff_list))
#print((time_diff_list))

time_diff_list = np.array(time_diff_list)
tdl_mean = np.mean(time_diff_list)
tdl_std = np.std(time_diff_list)

plt.hist(time_diff_list, bins =50)
plt.title(f"Time Difference between Coincident Events \nMean={tdl_mean:.2f} | STD={tdl_std:.2f}")
plt.xlabel("Time (ns)")
plt.ylabel("Frequency")
plt.show()
    