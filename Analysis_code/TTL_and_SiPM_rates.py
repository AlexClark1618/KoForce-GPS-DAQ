import numpy as np

import matplotlib.pyplot as plt

ttl = [(210.8,217.2), (268.2,317.4), (0,0), (207.8,229.3), (149.8, 157.4), (0,0), (261.6, 256.4), (248.6, 206.8), (174.9, 175.3), (246.9, 231.2)]

sipm = [(244.9, 242.8), (231, 300.3), (0,0), (209.9,241.8), (189.5, 225.8), (0,0), (319,323.4), (281.4,212.4), (218.7,224.5), (217,234.9)]


# Extract right and left sides separately
ttl_right = [t[0] for t in ttl]
ttl_left  = [t[1] for t in ttl]
sipm_right = [s[0] for s in sipm]
sipm_left  = [s[1] for s in sipm]

x = np.arange(1, len(ttl) + 1)  # detector numbers

# Plot with slight horizontal offsets so dots don’t overlap
plt.scatter(x, ttl_right, label='TTL Right', color='blue')
plt.scatter(x, ttl_left, label='TTL Left', color='red')
plt.scatter(x, sipm_right, label='SiPM Right', color='cyan', marker='x')
plt.scatter(x, sipm_left, label='SiPM Left', color='orange', marker='x')

plt.xlabel("Detector #")
plt.ylabel("Measured Rate")
plt.legend()
plt.title("TTL vs SiPM Rates per detector")
plt.grid(True)
plt.show()