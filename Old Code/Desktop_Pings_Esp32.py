import requests
import time
import numpy as np

esp32_ip = "http://192.168.0.19"  # Replace with your ESP32's IP

elapsed_time_list = []

with open('Time_diff.txt', 'w') as f: #Collecting elapsed time for analysis

    while True:
        try:
            start_time = time.time() # For testing timing of data transfer
            resp = requests.get(esp32_ip + "/data") 
            end_time = time.time()

            elapsed_time = end_time - start_time
            f.write(str(elapsed_time) +  "\n") #Must be a string
            f.flush() #Actually saves data

            if resp.status_code == 200:
                print("Data received:\n", resp.text)
                elapsed_time_list.append(elapsed_time)
                print(elapsed_time_list)

            elif resp.status_code == 204:
                print("No new data.")
            else:
                print("Unexpected response:", resp.status_code)

        except Exception as e: #So it doesnt hang
            print("Failed to connect:", e)
            print("Retrying in 1 second...")
            time.sleep(1)

        time.sleep(0.50) #Polling frequency

