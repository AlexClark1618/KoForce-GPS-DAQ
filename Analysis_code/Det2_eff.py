import numpy as np
import os
from collections import Counter
from natsort import natsorted
import matplotlib.pyplot as plt


def timestamp_ns(tup):
    """Combine ms and sub-ms into a single nanosecond timestamp"""
    return ((tup[6] * 1000000) + tup[7]) 

def folder_reader(folder_path): 
    folder_files_list = []     
    for filename in os.listdir(folder_path):
        #print(filename)
        if filename.startswith('gps_daq'):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):  # make sure it's a file
                file_name = file_path.replace("\\", "/")
                folder_files_list.append(file_name)
    return natsorted(folder_files_list)


def file_reader(folder_files_list):
    for file in folder_files_list: 
        print(file)
        read_data = []
        file_data = []

        with open(file, 'r') as f:

            next(f)

            for line in f:
                if line.startswith('[ESP]'): #Deals with the stupid marker in run 17
                    parts = line.strip().split(':')

                    parts2 = parts[1].strip().split(';')
                    
                    values = tuple(int(p.strip()) for p in parts2) #Converts all elements to ints for easier analysis

                    read_data.append(values)
                else:
                    parts = line.strip().split(';')
                    
                    values = tuple(int(p.strip()) for p in parts) #Converts all elements to ints for easier analysis

                    read_data.append(values)

            #print('file read')
            #(Data len, Error len, BH len, max Bh diff, BH period, BH<40ms, Array len, 
            # max array diff, avg rate, avg data transfer rate, nulls, reals, unique, mults, array eff,
            # null eff, data transfer eff, errors)
            data_list = [tup for tup in read_data if tup[0]==99]
            file_data.append(len(data_list))
            error_list = [tup for tup in read_data if tup[0]==100]
            #print('lists made')
            file_data.append(len(error_list))

            
            list_48 = [tup for tup in data_list if tup[1]==48 and tup[2]==0]
            list_48_events = np.array([tup[8] for tup in list_48])
            #print(max(np.diff(list_48_events)))
            file_data.append(len(list_48))
            file_data.append(max(np.diff(list_48_events)))


            timestamps_48 = np.array([timestamp_ns(tup) for tup in list_48])
            period_48 = np.diff(timestamps_48)
            #print(f'Avg BH Period:{np.mean(period_48)/1000000000}s')
            #print(f'Percentage of successive BH requests within 40ms:{(np.sum(period_48<40000000)/np.sum(period_48>0))*100}')
            avg_period = np.mean(period_48).item()
            avg_freq = 1/(avg_period/1000000000)
            file_data.append(avg_freq)
            file_data.append((np.sum(period_48<40000000)/np.sum(period_48>0))*100)


            list_180 = [tup for tup in data_list if tup[1]==180 and tup[2]==0] #and tup[4]!=1]
            list_180_events = np.array([tup[9] for tup in list_180])
            #print(len(list_180_events))
            #print(np.diff(list_180_events))
            #print(np.sum(np.diff(list_180_events)>2))
            #print(list_180)
            list_180_rises = [timestamp_ns(tup) for tup in list_180 if tup[3]==1]
            """         
            print(np.diff(list_180_rises))
            print(np.sum(np.diff(list_180_rises)<500000)/len(list_180_rises))

            print(min((np.diff(list_180_rises))))

            thresholds = (10000000000, 1000000000, 100000000,10000000,1000000,500000,100000,10000,1000)  # 1e3 → 1e6 (log scale)
            fractions = [np.sum(np.diff(list_180_rises) < t) / len(list_180_rises) for t in thresholds]

            # Plot
            plt.plot(thresholds, fractions, marker='o')
            plt.xscale('log')
            plt.xlabel('Threshold (ns)')
            plt.ylabel('Fraction of Events below Delta t threshold')
            #plt.title('Percentage of Events Seperated by Threshold')
            plt.grid(True)
            plt.show()"""

            file_data.append(len(list_180))
            file_data.append(max(np.diff(list_180_events)))
        
            rate_list = np.array([(tup[3]) for tup in data_list if tup[1]==180 and tup[2]==19])
            data_transfer_rate = np.array([(tup[4]/1000) for tup in data_list if tup[1]==180 and tup[2]==19])

            file_data.append(np.mean(rate_list))
            file_data.append(np.mean(data_transfer_rate))

            #print('read 48 and 180')
            #print(np.median(rate_list))
            #print(f'Standard Deviation of the Rate:{np.std(rate_list/2)}')

            event_num = -1
            list_180_null = []
            list_180_real = []
            list_180_real_unique = []
            list_180_mult =0
            list_180_total = []
            for tup in list_180:

                if tup[5] == 0:
                    list_180_null.append(tup)
                
                if tup[2] == 0 and tup[3]==1:
                    list_180_real.append(tup)

                    if tup[8] != event_num:
                        list_180_real_unique.append(tup)
                        event_num = tup[8]

                if tup[2] == 0:
                    list_180_total.append(tup)

            event_num = -1
            for tup in list_180:

                if tup[8] == event_num:
                    list_180_mult+=1
                event_num = tup[8]

                #print(list_180_mult)
                #print(list_180_real_unique)
                #print(f'# of BH requests:{len(list_48)}')
                #print(f'# of Det Events:{len(list_180_total)}')
                #print(f'# of Det Null Events:{len(list_180_null)}')
                #print(f'# of Det Real Events:{len(list_180_real)}')
                #print(f'# of Unique Det Events:{len(list_180_real_unique)}')

            file_data.append(len(list_180_null))
            file_data.append(len(list_180_real))
            file_data.append(len(list_180_real_unique))
            file_data.append(list_180_mult)
            rate = np.mean(rate_list).item()
            file_data.append(len(list_180_real)/(270*avg_freq*0.002*3600))
            file_data.append((len(list_180_null)/len(list_48))/0.567)
            file_data.append((len(list_180_real_unique)+len(list_180_null))/len(list_48))
            file_data.append(len(error_list)/3600)
        error_counter = Counter(tup[2] for tup in error_list)
        file_data.append(error_counter)

        cleaned_data = [x.item() if isinstance(x, np.generic) else x for x in file_data]

        #print(file_data)
        folder_data.append(cleaned_data)
        #print('file read')
    
    return folder_data

def folder_analysis(folder_data):

    folder_data = folder_data[:len(folder_data)-1] #Skips last file

    BH_lens = [row[2] for row in folder_data]
    BH_max_diff = [row[3] for row in folder_data]
    BH_period = [row[4] for row in folder_data]
    Array_lens = [row[6] for row in folder_data]
    Array_max_diff = [row[7] for row in folder_data]
    Rate = [row[8] for row in folder_data]
    Data_transfer_rate = [row[9] for row in folder_data]
    Nulls = [row[10] for row in folder_data]
    Real = [row[11] for row in folder_data]
    Unique = [row[12] for row in folder_data]
    Mults = [row[13] for row in folder_data]
    Array_eff = [row[14] for row in folder_data]
    Null_eff = [row[15] for row in folder_data]
    Data_transfer_eff = [row[16] for row in folder_data]
    Error_rate = [row[17] for row in folder_data]


    x = [(i+1) for i in range(len(Array_eff))]
    plt.plot(x, Array_eff,label = 'ESP Eff', color = 'red')
    plt.plot(x, Null_eff, label = 'Expected Nulls', color = 'green')
    plt.plot(x, Data_transfer_eff, label = 'Data Transfer Eff', color = 'blue')
    
    plt.xlabel("Cycle Number")
    plt.ylabel("Efficiency")
    plt.title("Run 24 Efficiencies")
    plt.legend()
    plt.show()

    print (
        f'BH_lens:{np.mean(BH_lens)}',f'BH_max_diff:{np.mean(BH_max_diff)}',
        f'BH_period:{np.mean(BH_period)}',f'Array_lens:{np.mean(Array_lens)}',
        f'Array_max_diff:{np.mean(Array_max_diff)}',f'Rate:{np.mean(Rate)}',
        f'Data_transfer_rate:{np.mean(Data_transfer_rate)}',f'Nulls:{np.mean(Nulls)}',
        f'Real:{np.mean(Real)}',f'Unique:{np.mean(Unique)}',            
        f'Mults:{np.mean(Mults)}',f'Array_eff:{np.mean(Array_eff)}',
        f'Null_eff:{np.mean(Null_eff)}',f'Data_transfer_eff:{np.mean(Data_transfer_eff)}',
        f'Error_rate:{np.mean(Error_rate)}'   
    )

if __name__ == "__main__":

    #(Data len, Error len, BH len, max Bh diff, BH period, BH<40ms, Array len, 
    # max array diff, avg rate, avg data transfer rate, nulls, reals, unique, mults, real rate, null rate, data transfer eff, error rate, errors)

    folder_path = 'C:\\Users\\aclark2\\Desktop\\ESP 32\\GPS Data\\Run 24'

    folder_files_list = folder_reader(folder_path)

    folder_data = []
    folder_data = file_reader(folder_files_list)
    print(folder_data)

    folder_analysis(folder_data)







    

    

   
        