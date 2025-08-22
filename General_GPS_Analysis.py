import matplotlib.pyplot as plt
import numpy as np



#Function to read data file (It should probably be general just clea and store all events into tuples)
def read_data(data_file:'str'):
    '''
    This function reads a provided data file and simply cleans it, strips, and splits it into a 
    list containing tuples of each timestamp
    '''
    read_data = []
    with open(data_file, 'r') as f:
        next(f) #Skip label row
        
        for line in f:
            # Strip whitespace and split on semicolons
            line = line.replace(',', ';')  # Replace comma with semicolon

            parts = line.strip().split(';')
            
            values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            if values[4] != 1: #Deals with encoding
                read_data.append(values)
        
        #print(len(read_data))
    return read_data

def event_grouper(data):
    Data = read_data(data)

    group_list = []
    temp_group_list = []
    last_event = Data[0][8]  # Start with the first event number

    for tup in Data:
        if tup[8] == last_event:
            temp_group_list.append(tup)
        else:
            # Save the group and start a new one
            group_list.append(temp_group_list)
            temp_group_list = [tup]
            last_event = tup[8]

    #Deals with last group
    if temp_group_list:
        group_list.append(temp_group_list)
    
    return group_list

def timestamp_ns(tup):
    """Combine ms and sub-ms into a single nanosecond timestamp"""
    return ((tup[6] * 1000000) + tup[7]) 


rise_times_list = []

#Function/s to filter artifacts
def filterer(data):
    pulse_width = []
    pulse_width_en = []
    clock_period = []
    clock_period_en = []
    #temp_list = [temp_list[-22]]
    #print(temp_list)
    for event_group in event_grouper(data):
        #print("Number of events:", len(event_grouper(data)))
        #print(f'eg:{event_group}')
        # Filter for ID == 20 only (borehole)
        bh_data = [t for t in event_group if t[1] == 20 and t[2] == 0 and t[4]==0] #ID and RF
        
        if not bh_data:
            continue  # Skip this group if no valid BH signature
        
        bh_ms = bh_data[0][6] 

        #print(bh_data)
        array_data = [t for t in event_group if t[1] == 200 and t[7] <= 10000000]# and t[7] <= 1000000 and abs(t[6]-(bh_data[0][6]))<100]
        #print(array_data)
        # Sort by timestamp (in case they're not sorted)
        #array_data.sort(key=timestamp_ns)
        
        # --- 1. Clock period (difference between successive cal == 0) ---
        rising_times = [timestamp_ns(t) for t in array_data if t[2] == 0]
        
        if len(rising_times) >= 2:
            period_diffs = np.diff(rising_times)
            avg_period = np.mean(period_diffs)
            clock_period.append(avg_period)
            clock_period_en.append(event_group[0][8])
            rise_times_list.append((avg_period,event_group[0][8]))
            #print(f"Event {event_group[0][8]}: avg clock period: {avg_period:.2f} ns")
        else:
            #print(f"Event {event_group[0][8]}: not enough rising edges to calculate period")
            pass

        # --- 2. Clock pulse width (cal == 0 followed by cal == 1 with same ch) ---
        # Optional: use (ch, cal) pairing
        pulse_durations = []
        used_indices = set()

               
        for i, t0 in enumerate(array_data):
            #print(i)
            if (t0[2] in (0,1)) and i not in used_indices:
                for j, t1 in enumerate(array_data):
                    #print(j)
                    if (
                        j != i and
                        t1[2] != t0[2] and
                        #t1[6] == t0[6] and  # same ms #Wont alwasy have the same ms timestamp, but hould in real life case
                        j not in used_indices
                    ):
                        # Match found
                        print((t1,t0))
                        dt = abs(timestamp_ns(t1) - timestamp_ns(t0))

                        #if dt<100000000: #Try to deal with the artifacts with way to large ns values
                        pulse_durations.append(dt)
                        used_indices.update([i, j])
                        break
        
        """
        for i in range(0, len(array_data) - 1, 2):
            t0, t1 = array_data[i], array_data[i+1]
            if t0[2] != t1[2] and t0[6] == t1[6]:  # make sure they’re opposite edges
                dt = abs(timestamp_ns(t1) - timestamp_ns(t0))
                pulse_durations.append(dt)
            else:
                print("Warning: same edge type in a pair:", t0, t1)
        """

        if pulse_durations:
            avg_pulse = np.mean(pulse_durations)
            pulse_width.append(avg_pulse)
            pulse_width_en.append(event_group[0][8])
            #print(f"Event {event_group[0][8]}: avg pulse width = {avg_pulse:.2f} ns\n")
        else:
            #print(f"Event {event_group[0][8]}: no valid pulse pairs found\n")
            pass
    
    return [(clock_period, clock_period_en), (pulse_width,pulse_width_en)]



#Plotting 
def pert_filter(data):
    data = np.array(data)

    low = np.percentile(data, 1)
    high = np.percentile(data, 99)

    # Filter values between 1st and 99th percentile
    filtered = data[(data >= low) & (data <= high)]
    return filtered

def no_filter_group_size_plotter(data):
    group_lengths = [len(group) for group in event_grouper(data) if len(group)>2] #Added length if 
    gl_mean = np.mean(np.array(group_lengths))
    gl_std = np.std(group_lengths)

    plt.figure(figsize=(8, 5))
    plt.hist(group_lengths, bins=range(min(group_lengths), max(group_lengths)+2), edgecolor='black', align='left')
    plt.title(f"Distribution of Entries per Event Number\n Mean: {gl_mean:.2f} | SD: {gl_std:.2f}")
    plt.xlabel("Number of SiPM Timestamps per Borehole Event (50ms timewindow)")
    plt.ylabel("Frequency")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    #plt.tight_layout()
    plt.show()

def clock_period_plotter(data):
    clock_period_y = [i for i in range(1,(len(pert_filter(filterer(data)[0][0]))+1))]
    #print("clock y len",len(clock_period_y))
    #print("cloclx len" , len(pert_filter(filterer(data)[0][0])))
    c_mean = np.mean(pert_filter(filterer(data)[0][0]))
    c_std = np.std(pert_filter(filterer(data)[0][0]))

    print(len(pert_filter(filterer(data)[0][0])))
    plt.scatter(pert_filter(filterer(data)[0][0]), clock_period_y)

    # Add labels and title
    plt.xlabel("Average Period Between SiPM Rise times (ns) (Time Differnce between successive rises within a given event)")
    plt.ylabel("Event Number")
    plt.title(f"Average Period Between SiPM Rise times per Event\n Mean:{c_mean:.2f} | SD: {c_std:.2f}")

    # Show grid and plot
    plt.grid(True)
    plt.show()

def pulse_width_plotter(data):
    pulse_width_y = [i for i in range(1,(len(pert_filter(filterer(data)[1][0]))+1))]
    p_w_mean = np.mean(pert_filter(filterer(data)[1][0]))
    p_w_std = np.std(pert_filter(filterer(data)[1][0]))

    plt.scatter(pert_filter(filterer(data)[1][0]),pulse_width_y)

    # Add labels and title
    plt.xlabel("Average SiPM Pulse Width (ns) (Time difference between successive rises and falls within a given event)")
    plt.ylabel("Event Number")
    plt.title(f"Average SiPM Width per Event\n Mean: {p_w_mean:.2f} | SD: {p_w_std:.2f}")

    # Show grid and plot
    plt.grid(True)
    plt.show()



if __name__ == "__main__": 
    data = 'Array Run (8-20-25) (BH + 2R).txt'

    #data = read_data(data_file)
    
    no_filter_group_size_plotter(data)
    clock_period_plotter(data)
    pulse_width_plotter(data)
    #print(rise_times_list)