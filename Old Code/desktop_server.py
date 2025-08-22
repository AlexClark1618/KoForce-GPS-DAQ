import socket
import struct 
import json

HOST = '' #Leave open 
PORT = 12345 # Test server port, choose different port if get an error

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

    s.bind((HOST, PORT))
    s.listen()
    print(f'Server listening on port {PORT}...')


    while True:
        conn, addr = s.accept()

        with conn:
            print('Connected by', addr)
            
            data = conn.recv(1024) # Bit length of messages up to 1024

            if data:
                message = data.decode('utf-8') #Decoding from utf-8
                print(message)

                #For messing with json format
                '''
                gps_data = json.loads(message)

                #This is just testing reading JSON format
                print("Encoded JSON:", data.hex()) 
                print("Recieved JSON:", gps_data)
                print("Latitude:", gps_data['latitude'])
                print("Longitude:", gps_data['longitude'])
                print("Timestamp:", gps_data['timestamp'])
                '''

            else:
                print("Decoding Failed")
