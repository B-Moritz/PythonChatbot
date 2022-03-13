# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 00:50:00 2022

@author: b-mor
"""

import socket
import logging
import threading
import argparse
import re
from queue import Queue 
import random
import time
import pdb
from select import select

class HostBot:
    
    def __init__(self):
        with open(".\\conversationInitiators.txt", "r") as file:
            self.convInitiators = file.read().split("\n")
        
        if self.convInitiators[-1] == '':
            self.convInitiators.pop()
        
        self.setCurInit()
        
    
    def getCurMsg(self):
        if time.time()-self.startExpir > 60:
            self.setCurInit()
        return self.curInit
    
    def setCurInit(self):
        self.curInit = self.convInitiators[random.randint(0, len(self.convInitiators)-1)]
        self.startExpir = time.time()

class SimpleChatServer:
    event = threading.Event()
    history = []
    
    def __init__(self, port):
        if type(port)!=int or port < 0 or port > 65535:
            raise ValueError(f"The provided port {port} is not valid." \
                             " Please provide a decimal number between 0 and 65535")
        
        self.port = port
        self.isRunning = False
        self.sendQueues = {}
        self.checkReadable = []
        self.checkWritable = []
        self.checkError = []
        
        
    def startService(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((socket.gethostname(), self.port))
        self.serverSocket.listen(5)
        self.checkReadable.insert(0, serverSocket) 
        
        logging.info("Service is listening to incomming connections on port %s.", str(self.port))
        
        print("Service is listening to incomming connections on port {}. \n".format(str(self.port)))
        self.isRunning = True
        
        mainThread = threading.Thread(target=self.mainThread, daemon=True)
        mainThread.start()
        
        while True:
            cmd = input("Please type \"exit\" to stop the service: \n")
            if cmd == "exit" or cmd == "Exit":
                print("Service is shuting down.")
                logging.info("The service is stoping due to user interaction.")
                self.event.set()
                break
        
        self.serverSocket.close()
        self.isRunning = False
        
    def mainThread(self):
        self.hostbot = HostBot()
        hostbotThread = threading.Thread(target=self.hostbotThread)
        hostbotThread.start()
        
        while True:
            readable, writable, err = select(self.checkReadable, self.checkWritable, self.checkError)
            
            client, src = self.serverSocket.accept()
            logging.info(f"New client connection accepted for source {src}.")
            curQueue = Queue()
            for i in range(len(self.history)):
                curQueue.put(self.history[i])
                
            self.sendQueues[src] = curQueue
            
            curThread = ClientThread(client, src, self.sendQueues, self.event, self.history)
            curThread.start()
            
    def hostbotThread(self):
        while not self.event.is_set():
            logging.info("A new message is sent from host")
            msg = self.hostbot.getCurMsg()
            self.history.append(msg)
            for queue in self.sendQueues.values():
                queue.put(msg)
            time.sleep(90)



if __name__=="__main__":
    
    #Handle command line argument 
    parser = argparse.ArgumentParser(description="This program starts a sigle threaded chat service.")
    parser.add_argument('-p', '--Port', nargs='?', const=2020, metavar="PORT",
                        type=int, help="The port number associated with the service")
    args = parser.parse_args()
    
    logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s', 
                        filename="./chatServer.log", level=logging.INFO)
    
    while
    
    