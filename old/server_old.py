# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 17:11:58 2022

@author: Bernt Olsen (s341528)   student ad OsloMet
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
        

class ClientThread(threading.Thread):
    endOfMsg = "::EOMsg::"
    def __init__(self, clientSocket, src, sendQueues, event, history):
        threading.Thread.__init__(self)
        self.clientSocket = clientSocket
        self.src = src
        self.rcv_msg = ""
        self.sendQueues = sendQueues
        self.cliQueue = sendQueues[self.src]
        self.event = event
        self.history = history
        
        
    def run(self):
        
        while not self.event.is_set():
            #pdb.set_trace()
            logging.info(f"Before send while loop. Size of queue: {self.cliQueue.qsize()}")
            for i in range(self.cliQueue.qsize()):
                try: 
                    self.sendToClient(self.cliQueue.get())
                except Exception as E:
                    logging.error(f"Error while trying to send: {str(E)}")
                    raise
                    
            try:    
                self.recFromClient()
            except Exception as E:
                logging.error(f"Error while trying to receive: {str(E)}")
                raise
                
        logging.info(f"Connection to {self.src} is closed")
        self.clientSocket.close()
        
        
    def sendToClient(self, msg):
        #Code from https://docs.python.org/3/howto/sockets.html
        msg = (msg + self.endOfMsg).encode()
        msgLen = len(msg)
        sent = 0
        logging.info(f"Sending messages to {self.src}")
        while sent < msgLen:
            curSent = self.clientSocket.send(msg[sent:])
            if curSent == 0:
                logging.error(f"The connection with client {self.src} is broken. No data was sent.")
                raise ConnectionError(f"The connection with client {self.src} is broken.")
                
            sent = sent + curSent
            
    def recFromClient(self):
        #pdb.set_trace()
        patern = re.compile(self.endOfMsg)
        logging.info(f"Receiving data from {self.src}")
        flag = True
        while flag:
            cur_rcv_msg = self.clientSocket.recv(1024).decode()
            self.rcv_msg = self.rcv_msg + cur_rcv_msg
            if bool(patern.search(self.rcv_msg)):
                #End of message
                msgList = self.rcv_msg.split(self.endOfMsg)
                self.rcv_msg = msgList.pop()
                
                for msg in msgList:
                    self.history.append(msg)
                    for key in self.sendQueues.keys():
                        if key != self.src:        
                            self.sendQueue[key].put(msg)
                flag = False
            elif len(cur_rcv_msg) == 0:
                logging.warning(f"Server is not receiving from {self.src}. Connection is closing!")
                self.event.set()
                flag = False
            logging.info("Loop receiveing: {len(cur_rcv_msg)}")
            

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
        
        
    def startService(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((socket.gethostname(), self.port))
        self.serverSocket.listen(5)
        
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
    
    server = SimpleChatServer(args.Port)
    server.startService()
    
                
            
                
            

