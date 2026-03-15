import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import os
from natsort import natsorted
from scipy import stats


def error_file_parser(error_file):
    with open(error_file, 'r') as ef:

        for line in ef:

            parts = line.strip().split(':')
            parts = parts[1].strip().split(';')

            try:
                values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis
            except Exception:
                continue
        
            if values[0] == 100 and values[2] == 7:

                detector_id = values[1]
                error_dict[detector_id].append(values) 
                
    for (key1, val1) in det_dict.items(): 
            
        for (key2, val2) in error_dict.items():

            if val1 == key2:

                error_count_dict[key1] = len(val2)

    return error_count_dict
    

# region              
BH_list = []
Veto_list = []
det1_list = []
det2_list = []
det3_list = []
det4_list = []
det5_list = []
det6_list = []
det7_list = []
det8_list = []
det9_list = []
det10_list = []
all_data = []

det1_rate98_list = []
det2_rate98_list = []
det3_rate98_list = []
det4_rate98_list = []
det5_rate98_list = []
det6_rate98_list = []
det7_rate98_list = []
det8_rate98_list = []
det9_rate98_list = []
det10_rate98_list = []
#endregion

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

def read_data(data_file, single_file):

    with open(data_file, 'r') as f:
        if single_file:
            next(f)

        unique_esp_macs = []

        for line in f:

            parts = line.strip().split(';')
            #print(parts)
            values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

            if values[0] == 98:  

                if values[1]==112:
                    det1_rate98_list.append(values)
                if values[1]==180:
                    det2_rate98_list.append(values)
                if values[1]==172:
                    det3_rate98_list.append(values)
                if values[1]==64:
                    det4_rate98_list.append(values)
                if values[1]==216:
                    det5_rate98_list.append(values)
                if values[1]==252:
                    det6_rate98_list.append(values)
                if values[1]==224:
                    det7_rate98_list.append(values)
                if values[1]==20:
                    det8_rate98_list.append(values) 
                if values[1]==104:
                    det9_rate98_list.append(values)
                if values[1]==164:
                    det10_rate98_list.append(values)

            elif values[0]==99 and values[6]!=0: #Real data
                if values[6]<604800000 and values[7]<1000000: #Ignore nonsense ms and ns timestamps
                    all_data.append(values)

                if values[1] not in unique_esp_macs:
                    unique_esp_macs.append(values[1])

                if values[1]==48:
                    BH_list.append(values)
                if values[1]==16:
                    Veto_list.append(values)
                if values[1]==112:
                    det1_list.append(values)
                if values[1]==180:
                    det2_list.append(values)
                if values[1]==172:
                    det3_list.append(values)
                if values[1]==64:
                    det4_list.append(values)
                if values[1]==216:
                    det5_list.append(values)
                if values[1]==252:
                    det6_list.append(values)
                if values[1]==224:
                    det7_list.append(values)
                if values[1]==20:
                    det8_list.append(values)
                if values[1]==104:
                    det9_list.append(values)
                if values[1]==164:
                    det10_list.append(values)

    print("Read data complete") 
    print(f'Unique ESPs in data file: {unique_esp_macs}')
    print(f'ESP Instance Counter:\n BH:{len(BH_list)}\n Veto:{len(Veto_list)}\n Det1:{len(det1_list)}\n Det2:{len(det2_list)}\n Det3:{len(det3_list)}\n Det4:{len(det4_list)}\n Det5:{len(det5_list)}\n Det6:{len(det6_list)}\n Det7:{len(det7_list)}\n Det8:{len(det8_list)}\n Det9:{len(det9_list)}\n Det10:{len(det10_list)}\n')
    
    return len(unique_esp_macs)

def gps_daq_health_variables():#cycle_start, cycle_end, plotting):
    global data_integrity

    folder_files_list= folder_reader(data_folder)

    data_integrity_list_per_cycle = []

    mod_folder_list = len(folder_files_list)%5
    max_len = len(folder_files_list)- mod_folder_list

    for i in range(1, max_len, 5):#[cycle_start-1:cycle_end]:
        
        file = folder_files_list[i]
        print(file)

        for lst in (BH_list, Veto_list, det1_list, det2_list, det3_list, det4_list, det5_list, det6_list, det7_list, det8_list, det9_list, det10_list, det1_rate98_list, det2_rate98_list, det3_rate98_list, det4_rate98_list, det5_rate98_list, det6_rate98_list, det7_rate98_list, det8_rate98_list, det9_rate98_list, det10_rate98_list):
            lst.clear()

        read_data(file, True)

        BH_request_count = sum(1 for tup in BH_list if tup[2]==0 and tup[4]==0)
        BH_file_live_time = BH_request_count * 0.002
        BH_rate = BH_request_count / 3600

        Veto_request_count = sum(1 for tup in Veto_list if tup[2]==0)
        Veto_file_live_time = Veto_request_count * 0.002
        Veto_rate = Veto_request_count / 3600

        total_requests = BH_request_count + Veto_request_count
        request_rate = total_requests / 3600
        file_live_time = BH_file_live_time + Veto_file_live_time

        det_list = [det1_list, det2_list, det3_list, det4_list, det5_list, det6_list, det7_list, det8_list, det9_list, det10_list]
        det_rate98_list = [det1_rate98_list, det2_rate98_list, det3_rate98_list, det4_rate98_list, det5_rate98_list, det6_rate98_list, det7_rate98_list, det8_rate98_list, det9_rate98_list, det10_rate98_list]

        for det, rate98 in zip(det_list, det_rate98_list):

            if len(det)>0:
                try:
                    det_array = np.array(det)
                    det_rate98_array = np.array(rate98)

                    det_ch0_data_count = sum(1 for tup in det_array if tup[2]==0 and tup[4]==0)
                    det_ch1_data_count = sum(1 for tup in det_array if tup[2]==0 and tup[4]==1)

                    det_ch0_rates = (det_rate98_array[:,2] / (det_rate98_array[:,4]/1000))
                    det_ch0_rate = np.mean(det_ch0_rates)
                    det_ch1_rates = (det_rate98_array[:,3] / (det_rate98_array[:,4]/1000))
                    det_ch1_rate = np.mean(det_ch1_rates)
                
                    det_meas_rate = (det_ch0_data_count + det_ch1_data_count) /3600

                    det_calc_rate = (det_ch0_rate+det_ch1_rate) * request_rate * 0.002
                    det_data_integrity = det_meas_rate / det_calc_rate
                    data_integrity_list_per_cycle.append(det_data_integrity)
                except Exception:
                    data_integrity_list_per_cycle.append(0)

        data_integrity.append(data_integrity_list_per_cycle)
        data_integrity_list_per_cycle = []

    data_integrity = np.array(data_integrity)
    for i in range(10):

        avg_det_eff.append(np.sum(data_integrity[:,i])/len(data_integrity))
    
    return avg_det_eff
        
def error_vs_integrity(data1, data2):

    x = np.array(list(data1.values()))
    y = data2



    m, b = np.polyfit(x, y, 1)

    # Predicted values
    y_fit = m*x + b

    residuals = y - y_fit
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)

    r_squared = 1 - (ss_res / ss_tot)
    print("R²:", r_squared)

    plt.scatter(x, y)
    plt.plot(x, y_fit , color = 'r')
    plt.xlabel("Error Count")
    plt.ylabel("Detector Efficiency")
    plt.title("Detector Efficiency Per Error Count")
    plt.show()

    


        


if __name__ == "__main__":

    #Run ID and folder paths
    run_num = 'Run_0020_20260227'

    save_folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\Graphs\\'
    save_folder = os.path.join(save_folder_path, run_num)

    os.makedirs(save_folder, exist_ok=True)  

    data_folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\'
    data_folder = os.path.join(data_folder_path, run_num)

    error_file = 'error_log.txt'
    error_file_path = os.path.join(data_folder, error_file)




    # region ###Global Variables###
    error_dict = defaultdict(list)
    det_dict = {1:112, 2:180, 3:172, 4:64, 5:216, 6:252, 7:224, 8:20, 9:104, 10:164}
    error_count_dict  = defaultdict()
    avg_det_eff = []

    det1_data_int = []
    det2_data_int = []
    det3_data_int = []
    det4_data_int = []
    det5_data_int = []
    det6_data_int = []
    det7_data_int = []
    det8_data_int = []
    det9_data_int = []
    det10_data_int = []
    
    data_integrity = []
    # endregion
    
    error_count_dict = error_file_parser(error_file_path)
    avg_det_eff = gps_daq_health_variables()#1, 24, False)    
    error_vs_integrity(error_count_dict, avg_det_eff)