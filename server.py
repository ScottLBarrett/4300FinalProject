import socket
import math
import matplotlib.pyplot as plt
import sys
import random
import time
import os
import json


LOWEST_BITRATE = int(1024*200)      # 200 KBps = 0.195 MBps
LOW_BITRATE = int(1024*512)         # 512 KBps = 0.5 MBps
MEDIUM_BITRATE = int(1024*1024)     # 1 MBps
HIGH_BITRATE = int(1024*1024*2)     # 2 MBps
HIGHEST_BITRATE = int(1024*1024*4)  # 4 MBps

SECONDS_PER_CHUNK = 3 #The server will send the "videos" in this many second chunks

manifest_file = {
    "lowest": {"bitrate": LOWEST_BITRATE}, 
    "low": {"bitrate": LOW_BITRATE}, 
    "medium": {"bitrate": MEDIUM_BITRATE},
    "high": {"bitrate": HIGH_BITRATE},
    "highest": {"bitrate": HIGHEST_BITRATE} 
}

def main():

    if len(sys.argv) > 1:

        # Define the IP address and port of the receiver
        server_ip = 'localhost'
        server_port = int(sys.argv[1])

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((server_ip, server_port))
        server_socket.listen(10000)
        print(f"Server started on port {server_port}")

        while True:
            try:
                client_connection, _ = server_socket.accept()
                handleRequest(client_connection)
            except KeyboardInterrupt:
                break
            except:
                print("An error occured")

    else:
        print("Wrong arguments\nProvide receiver port.")

def handleRequest(client_connection):

    request = client_connection.recv(1024)
    print(f"RECEIEVED: {request.decode()}")

    response = "unknown request".encode()
    if request.decode() == "MANIFEST":
        response = json.dumps(manifest_file).encode()
        print("SENDING: Manifest File")
        client_connection.sendall(response)

    else:
        for key in manifest_file:
            
            if request.decode() == key:
                number_of_bytes = SECONDS_PER_CHUNK * manifest_file[key]["bitrate"]
                response = os.urandom(number_of_bytes)
                print(f"SENDING: {number_of_bytes} random bytes")
                
                client_connection.sendall(response)

    client_connection.close()

if __name__ == '__main__':
    main()
