import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import re

# Prepare storage
reconnect_times = defaultdict(list)

# Regex to extract timestamp and IP
pattern = re.compile(r"([0-9]+\.[0-9]+): Reconnected from \('([\d\.]+)', \d+\)")

with open("C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\connection_log.txt", "r") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            timestamp = float(match.group(1))
            ip = match.group(2)
            reconnect_times[ip].append(timestamp)

# Convert to normal dict if you want
reconnect_times = dict(reconnect_times)

# --- Print example ---
for ip, times in reconnect_times.items():
    print(f"{ip}: {times}")



     