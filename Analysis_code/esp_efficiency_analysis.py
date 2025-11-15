import numpy as np
import matplotlib.pyplot as plt
import os
'''
Decription: 
    This code attempt to measure the efficiency of each airshower detector's ESP. It utilizes rates measured from
    the CFD boards 
'''

def folder_reader(folder_path): 
    folder_files_list = []     
    for filename in os.listdir(folder_path):
        if filename.startswith('gps_daq'):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):  # make sure it's a file
                file_name = file_path.replace("\\", "/")
                folder_files_list.append(file_name)
    return folder_files_list

def file_reader_plotter(DATA: list, Mode):

    file_list = []
    measured_list = []
    eff_per_file = []


    for file in DATA: 
        det_1 = 0
        det_2 = 0
        det_3 = 0
        det_4 = 0
        det_5 = 0
        det_6 = 0
        det_7 = 0
        det_8 = 0
        det_9 = 0
        det_10 = 0
        BH = 0

        with open(file, 'r') as f:
            next(f) #Skip header

            line_count = 0 

            for line in f:
                parts = line.strip().split(';')
                
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis
                
                line_count += 1 #Counts total number of lines in file

                #Counts occurances of each esp in the data file
                if values[1]==48:
                    BH += 1
                if values[1]==112:
                    det_1 += 1
                if values[1]==180:
                    det_2 += 1
                if values[1]==172:
                    det_3 += 1
                if values[1]==64:
                    det_4 += 1
                if values[1]==232:
                    det_5 += 1
                if values[1]==252:
                    det_6 += 1
                if values[1]==224:
                    det_7 += 1
                if values[1]==188:
                    det_8 += 1
                if values[1]==104:
                    det_9 += 1
                if values[1]==164:
                    det_10 += 1
                #else:
                    #print("Unknown ID")

            det_info = (BH ,det_1, det_2, det_3, det_4, det_5, det_6, det_7, det_8, det_9, det_10)
            det_info = det_info + (sum(det_info),) + (line_count,) #Just for debugging to see total number of lines = the sum of the parts

            file_list.append(file)
            measured_counts = np.array(det_info[:11])//2
            measured_list.append(measured_counts)
            #print(measured_counts)
            eff_per_file.append(measured_counts/ expected_counts)#Generate a list of statistics across multiple files 

    if Mode == 0: #For plotting single files
        for det_info, file_name in zip(measured_list, file_list):
            # Bar width and positioning for side-by-side bars
            bar_width = 0.35
            names = ['BH', 'Det1', 'Det2', 'Det3', 'Det4', 'Det5', 'Det6', 'Det7', 'Det8', 'Det9', 'Det10']
            items = np.arange(1,12)
            x = np.arange(len(items))

            plt.figure(figsize=(10, 5))

            # Plot measured and expected side-by-side
            plt.bar(x - bar_width/2, det_info, bar_width, label='Measured', alpha=0.8)
            plt.bar(x + bar_width/2, expected_counts, bar_width, label='Expected', alpha=0.8)

            # Labels and aesthetics
            plt.xticks(x, [f'{i}' for i in names])
            plt.ylabel('Count')
            plt.title(f'Measured vs Expected Counts (File:{file_name})')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
    
    if Mode == 1: #For plotting average of multiple files

        eff_per_file = np.array(eff_per_file)
        
        std = np.std(eff_per_file, axis=0)

        average_effs = np.sum(eff_per_file, axis=0)/len(eff_per_file)

        # Bar width and positioning for side-by-side bars
        bar_width = 0.35
        names = ['BH', 'Det1', 'Det2', 'Det3', 'Det4', 'Det5', 'Det6', 'Det7', 'Det8', 'Det9', 'Det10']

        plt.errorbar(names, average_effs, yerr=std, fmt='o', capsize=5, ecolor='black', color='blue', markersize=6)

        plt.xlabel("Det #")
        plt.ylabel("ESP Efficiency (%)")
        plt.title("Efficiency Per Detector ESP")
        plt.grid(True)
        plt.show()
    

def read_error_log(error_file):

    reboot_time = []

    with open(error_file, 'r') as f:
        for line in f:
            line = line.strip()

            if line.startswith("[ESP]:"):

                parts = line.split(":") #Remove [ESP] marker

                parts = parts[1].strip().split(";") #Split info 

                values = tuple(int(p.strip()) for p in parts) #Convert info to integers

                if values[2] == 15: #Reboot marker
                    if values[3]<30000: #Effectively trying to ignore the first reboot, which will by nature be large
                        reboot_time.append(values[3])
        
        return reboot_time

###Main###
if __name__ == "__main__":
    BH_rate = 1.8 * 3600
    arr_rate = 1.8 * 0.002 * 3600
    """
    expected_counts = np.array((BH_rate, arr_rate * 201, arr_rate*524, arr_rate*341, arr_rate*386, arr_rate*179, 
                        arr_rate*317, arr_rate*283, arr_rate*394, arr_rate*211, arr_rate*335))
    """

    expected_counts = np.array((BH_rate, arr_rate * 428, arr_rate*585.6, arr_rate*375.1, arr_rate*437.1, arr_rate*307.2, 
                        arr_rate*348.7, arr_rate*518, arr_rate*455.4, arr_rate*350.2, arr_rate*478.1))

    folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\Run20251007'

    DATA_LIST = folder_reader(folder_path)
    print('DATA_LIST:', DATA_LIST)

    error_file = "C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\Run20251008\\error_log.txt"

    file_reader_plotter(DATA_LIST, Mode = 1)


    #Reboot Deadtime          
    reboot_time = read_error_log(error_file)
    reboot_time_len = len(reboot_time)
    print(f'Total Rebbot Deadtime for Det 8: {(np.sum(reboot_time) + (10000 * reboot_time_len))/1000}')




















