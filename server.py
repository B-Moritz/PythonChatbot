# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 17:11:58 2022

@author: Bernt Olsen (s341528)   student ad OsloMet
"""

import socket
import logging
import os
import threading
import argparse
import re
from queue import Queue 
import random
import time 

class HostBot:
    
    def __init__(self):
        with open(".\\conversationInitiators.txt", "r") as file:
            self.convInitiators = file.read().split("\n")
        
        if self.convInitiators[-1] == '':
            self.convInitiators.pop()
        
        print(self.convInitiators)
        
    
    def getCurMsg(self):
        if time.time()-self.startExpir > 60:
            self.setCurInit()
        return self.curInit
    
    def setCurInit(self):
        self.curInit = self.convInitiators[random.randint(0, len(self.convInitiators)-1)]
        self.startExpir = time.time()
        

class ClientThread(threading.Thread):
    def __init__(self, clientSocket, src, hostbot):
        self.Thread.__init__()
        self.clientSocket = clientSocket
        self.src = src
        self.hostbot
        
    def run(self):
        msg = self.hostbot.getCurMsg()
        self.sendToClient(msg)
        
    def sendToClient(self, msg):
        #Code from https://docs.python.org/3/howto/sockets.html
        msg = msg.encode()
        msgLen = len(msg)
        sent = 0
        while sent < msgLen:
            curSent = self.clientSocket.send(msg[sent:])
            if curSent == 0:
                logging.error(f"The connection with client {self.src} is broken.")
                raise ConnectionError(f"The connection with client {self.src} is broken.")
                
            sent = sent + curSent
            
    def recFromClient(self):
        while not curRec == 0:
            rcv_msg = self.clientSocket.recv()
            
    
            
        
    

class SimpleChatServer:
    
    def __init__(self, port):
        if type(port)!=int or port < 0 or port > 65535:
            raise ValueError(f"The provided port {port} is not valid." \
                             " Please provide a decimal number between 0 and 65535")
        
        self.port
        self.isRunning = False
        self.responseQueues = {}
        
        
    def startService(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bin((socket.gethostname(), self.port))
        self.serverSocket.listen(5)
        
        print("Service is listening to incomming connections on port {self.port}. \n")
        self.isRunning = True
        
        mainThread = threading.Thread(target=self.mainThread, daemon=True)
        mainThread.start()
        
        while True:
            cmd = input("Please type \"exit\" to stop the service: \n")
            if cmd == "exit" or cmd == "Exit":
                print("Service is shuting down.")
                break
        
        self.serverSocket.close()
        self.isRunning = False
        
    def mainThread(self):
        
        while not self.event.is_set():
            client, src = self.serverSocket.accept()
            self.responseQueues[src] = Queue()
            self.hostbot = HostBot()
            
            curThread = threading()
            
            
            
        
    



if __name__=="__main__":
    
    #Handle command line argument 
    parser = argparse.ArgumentParser(description="This program starts a sigle threaded chat service.")
    parser.add_argument('-p', '--Port', nargs='?', const=2020, metavar="PORT",
                        type=int, help="The port number associated with the service")
    parser.parse_args()
    
    logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s', 
                        filename="./httpServer.log", level=logging.INFO)
    
                
            
                
            

