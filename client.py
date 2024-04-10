import socket
import random
import sys
import time
import json
import threading
import matplotlib.pyplot as plt

MEASURING_TIMER = 5 #Measure the network speed after this amount of seconds

VIDEO_LENGTH = 5*60

manifest_file = {}
request_type = "high"
static_request = False

server_ip = 'localhost'
server_port = -1    #Gets set based on args

video_buffer = b''
seconds_in_buffer = 0
buffer_lock = threading.Lock()

min_speed = -1  #Gets set based on args
max_speed = -1  #Gets set based on args
current_net_speed = -1

total_seconds_receieved = 0

starting_time = time.time()

data_in_buffer_graph = []   #Will append a tuple of (timestamp, buffer size) every time the buffer is changed
network_speed_graph = []    #Will append a tuple of (timestamp, network speed) every time the net speed is changed
bitrate_graph = []          #Will append a tuple of (timestamp, bitrate chosen) every time the chosen bitrate is changed
buffering_timestamps = []   #A list of timestamps of when the video had to be buffered (wasn't downloaded quick enough)

def main():
    global server_port
    global min_speed
    global max_speed
    global request_type
    global static_request

    if(len(sys.argv) > 3):

        # Define the port based on args
        server_port = int(sys.argv[1])

        #Set the min and max network speeds based on args
        min_speed = float(sys.argv[2])
        max_speed = float(sys.argv[3])

        if len(sys.argv) > 4:
            static_request = True

        try:
            getManifestFile()

            bitrate_graph.append((time.time()-starting_time, round(manifest_file[request_type]["bitrate"]/1024/1024, 2)))

            requesting_thread = threading.Thread(target=requestVideo)
            requesting_thread.start()

            playing_thread = threading.Thread(target=playVideo)
            playing_thread.start()

            net_speed_thread = threading.Thread(target=setNetSpeed)
            net_speed_thread.start()

            requesting_thread.join()
            playing_thread.join()
            net_speed_thread.join()

            print(f"Finished everything, took {round(time.time() - starting_time, 2)} seconds")
            graphData()
        
        except KeyboardInterrupt:
            print("Sayonara")

    else:
        print("Wrong arguments\nProvide listen port, minimum network speed(MB/s), and max network speed(MB/s).")

#Requests the manifest file from the server
def getManifestFile():
    global manifest_file

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    client_socket.connect((server_ip, server_port))
    client_socket.sendall("MANIFEST".encode())

    manifest_file = json.loads(client_socket.recv(1024).decode())

    print(f"Receieved Manifest File:\n" + json.dumps(manifest_file))

#Continually requests chunks of video until it's received the entire video
def requestVideo():
    global video_buffer
    global seconds_in_buffer
    global total_seconds_receieved

    measuring_timer = time.time()
    bytes_for_measuring = 0

    while total_seconds_receieved < VIDEO_LENGTH:
    
        #Every so often, measure the average network speed and select the best bitrate
        if not static_request and time.time() - measuring_timer > MEASURING_TIMER:
            selectBitrate(measuring_timer, bytes_for_measuring)
            bytes_for_measuring = 0
            measuring_timer = time.time()

        #Create the socket, connect, and send the request
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, server_port))

        print(f"\nSENDING: {request_type}")
        client_socket.sendall(request_type.encode())

        received_data = b''
        second_timestamp = time.time()
        bytes_this_second = 0
        start = time.time()
        while True:

            if time.time() - second_timestamp > 1:
                second_timestamp = time.time()
                bytes_this_second = 0

            if bytes_this_second < current_net_speed:
                data = client_socket.recv(20480) 
                if not data:
                    break  # End of data
                received_data += data
                bytes_this_second += len(data)
                bytes_for_measuring += len(data)
        
        buffer_lock.acquire()
        data_in_buffer_graph.append((time.time() - starting_time, round(len(video_buffer)/1024/1024, 2)))
        video_buffer += received_data
        seconds_in_buffer += len(received_data) / manifest_file[request_type]["bitrate"]
        data_in_buffer_graph.append((time.time() - starting_time, round(len(video_buffer)/1024/1024, 2)))
        buffer_lock.release()
        
        print(f"Received entire chunk in {round(time.time() - start, 2)} seconds")

        total_seconds_receieved += len(received_data) / manifest_file[request_type]["bitrate"]
    
    print("Receieved entire video, waiting for playing to finish")
    bitrate_graph.append((time.time()-starting_time, round(manifest_file[request_type]["bitrate"]/1024/1024, 2)))

#Based on the amount of bytes given and timestamp, choose the proper bitrate
def selectBitrate(measuring_timer, bytes_for_measuring):
    global request_type

    bitrate_graph.append((time.time()-starting_time, round(manifest_file[request_type]["bitrate"]/1024/1024, 2)))

    average_speed = bytes_for_measuring / (time.time() - measuring_timer)

    selected_bitrate = "lowest"
    for key in manifest_file.keys():
        
        #If the average speed was faster than this key, set it to this key
        if average_speed > manifest_file[key]["bitrate"]:
            selected_bitrate = key

    if selected_bitrate != request_type:
        request_type = selected_bitrate
    
    
    bitrate_selected = manifest_file[selected_bitrate]["bitrate"]
    bitrate_graph.append((time.time()-starting_time, round(bitrate_selected/1024/1024, 2)))

    print(f"\nSELECTED {selected_bitrate} bitrate = {round(bitrate_selected/1024/1024, 2)}MBps")
    print(f"Average speed: {round(average_speed/1024/1024, 2)}MBps")

#Every 3 seconds, set a new network speed
def setNetSpeed():
    global current_net_speed

    current_net_speed = random.uniform(min_speed *1024*1024, max_speed *1024*1024)
    network_speed_graph.append((time.time()-starting_time, round(current_net_speed/1024/1024, 2)))
    print(f"Network speed set to {round(current_net_speed/1024/1024, 2)}MBps")

    timer = time.time()
    while total_seconds_receieved < VIDEO_LENGTH:

        if time.time() - timer > 3:
            timer = time.time()

            network_speed_graph.append((time.time()-starting_time, round(current_net_speed/1024/1024, 2)))
            current_net_speed = random.uniform(min_speed *1024*1024, max_speed *1024*1024)
            network_speed_graph.append((time.time()-starting_time, round(current_net_speed/1024/1024, 2)))

            print(f"Network speed set to {round(current_net_speed/1024/1024, 2)}MBps")
            

def playVideo():
    global video_buffer
    global seconds_in_buffer

    buffering_alert = True

    buffer_lock.acquire()
    while total_seconds_receieved < VIDEO_LENGTH or seconds_in_buffer > 0:
        amount_of_bytes = len(video_buffer)
        amount_of_seconds = seconds_in_buffer
        if seconds_in_buffer >= 5 or total_seconds_receieved >= VIDEO_LENGTH:
            video_buffer = b''
            seconds_in_buffer = 0
            data_in_buffer_graph.append((time.time() - starting_time, round(amount_of_bytes/1024/1024, 2)))
            data_in_buffer_graph.append((time.time() - starting_time, 0))
            buffer_lock.release()

            buffering_alert = True
            print(f"\n************\nPlaying video for {amount_of_seconds} seconds\n************")
            time.sleep(amount_of_seconds)
        else:
            buffer_lock.release()
            if buffering_alert:
                print("\n************\nBUFFERING VIDEO\n************")
                buffering_alert = False
                buffering_timestamps.append(time.time() - starting_time)
        
        buffer_lock.acquire()

    print("PLAYING THREAD COMPLETE")

def graphData():
    #Plots the amount of data in the buffer over time
    timestamps, data_in_buffer = zip(*data_in_buffer_graph)
    plt.figure(1)
    plt.title("Amount of Data in Buffer Over Time")
    plt.xlabel("Time (Seconds)")
    plt.ylabel("Amount of Data in Buffer (MB)")
    plt.plot(timestamps, data_in_buffer, color='blue', label="Data in buffer")
    for i in range(len(buffering_timestamps)):
        if i == 0:
            plt.axvline(x=buffering_timestamps[i], color='red', label="Spots where buffering occured")
        else:
            plt.axvline(x=buffering_timestamps[i], color='red')
    plt.legend()

    #Plots the network speed & bitrate selected over time
    timestamps, net_speed = zip(*network_speed_graph)
    plt.figure(2)
    plt.title("Network Speed / Bitrate Chosen Over Time")
    plt.xlabel("Time (Seconds)")
    plt.ylabel("Megabytes per Second")
    plt.plot(timestamps, net_speed, label='Network Speed', color='blue')

    timestamps, bitrate = zip(*bitrate_graph)
    plt.plot(timestamps, bitrate, label='Bitrate Chosen', color='red')
    plt.legend()

    plt.show()

if __name__ == '__main__':
    main()
