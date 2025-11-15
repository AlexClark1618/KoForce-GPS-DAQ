import matplotlib.pyplot as plt
import numpy as np

with open("Time_diff.txt", 'r') as f:
    lines = f.readlines()


data_list = []
for line in lines:
    data_list.append(float(line.strip()))

#print (data_list)

data_list = np.array(data_list)
print()
low, high = np.percentile(data_list, [1, 99])
filtered = data_list[(data_list >= low) & (data_list <= high)]

plt.hist(data_list)
plt.xlabel('Time (s)')
plt.ylabel('Frequency')
plt.show()

plt.hist(filtered, bins=50)
plt.xlabel('Time (s)')
plt.ylabel('Frequency')
plt.title(f'Elapsed Time (1-99%) \n Mean:{np.mean(filtered)}')
plt.show()