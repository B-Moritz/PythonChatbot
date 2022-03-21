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
#import pdb
from select import select
import datetime

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
        self.curInit = "Host: " + self.convInitiators[random.randint(0, len(self.convInitiators)-1)]
        self.startExpir = time.time()

class SimpleChatServer:
    event = threading.Event()
    history = []
    endOfMsg = "::EOMsg::"
    maxRcv = 100
    botnamePattern = re.compile("^(.*): ")
    
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
        self.recvRest = {}
        self.closeNext = []
        self.activeThreads = Queue()
        
        
    def startService(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((socket.gethostname(), self.port))
        self.serverSocket.listen(5)
        self.checkReadable.insert(0, self.serverSocket) 
        
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
        
        mainThread.join(15)
        self.serverSocket.close()
        self.isRunning = False
        
    def mainThread(self):
        self.hostbot = HostBot()
        hostbotThread = threading.Thread(target=self.hostbotThread)
        hostbotThread.start()
        
        #pdb.set_trace()
        
        while not self.event.is_set():
            readable, writable, err = select(self.checkReadable, self.checkWritable, self.checkError, 10)
            
            for client in readable:
                if client is self.serverSocket:
                    curThread = threading.Thread(target=self.acceptConnection)
                    curThread.start()
                    self.activeThreads.put(curThread)
                else:
                    curThread = threading.Thread(target=self.recvFromClient, args=(client, ))
                    curThread.start()
                    self.activeThreads.put(curThread)
                    
            for client in writable:
                curThread = threading.Thread(target=self.sendToClient, args=(client, ))
                curThread.start()
                self.activeThreads.put(curThread)
           
            
            while not self.activeThreads.empty():
                self.activeThreads.get().join()
                
            while len(err) != 0:
                self.removeClient(err.pop())
                
                
            while len(self.closeNext) != 0:
                self.removeClient(self.closeNext.pop())
        
        hostbotThread.join()
            
    def hostbotThread(self):
        while not self.event.is_set():
            logging.info("A new message is sent from host")
            msg = self.hostbot.getCurMsg()
            self.history.append(msg)
            for queue in self.sendQueues.values():
                queue[0].put(msg)
            time.sleep(90)
            
    def acceptConnection(self):
        client, src = self.serverSocket.accept()
        logging.info(f"New client connection accepted for source {src}.")
        curQueue = Queue()
        for i in range(len(self.history)):
            curQueue.put(self.history[i])
            
        self.sendQueues[client.getpeername()] = [curQueue, "", ""]
        
        self.checkReadable.append(client)
        self.checkWritable.append(client)
        self.checkError.append(client)
    
    def sendToClient(self, cliSock):
        
        sendQueue = self.sendQueues[cliSock.getpeername()][0]
        
        for i in range(sendQueue.qsize()):
            logging.info(f"Sending message to {cliSock.getpeername()}")
            msg = (sendQueue.get() + self.endOfMsg).encode()
            msgLen = len(msg)
            sentBytes = 0
            while sentBytes < msgLen:    
                try:
                    curSent = cliSock.send(msg[sentBytes:])
                except (ConnectionAbortedError, ConnectionResetError) as E:
                    logging.warning(f"The connection with the client {cliSock.getpeername()} has ended: {E}")
                    self.closeNext.append(cliSock)
                    return
                
                sentBytes += curSent
                if curSent == 0:
                    logging.error(f"The connection with client {cliSock.getpeername()} is broken. No data was sent.")
                    self.closeNext.append(cliSock)
                
    def recvFromClient(self, cliSock):
        logging.info(f"Receiving from client {cliSock.getpeername()}")
        pattern = re.compile(self.endOfMsg)
        clientList = self.sendQueues[cliSock.getpeername()]
        data_recv = clientList[1]
        cur_recv = ""
        
        while not bool(pattern.search(data_recv)) and len(data_recv) < self.maxRcv: 
            
            try:
                cur_recv = cliSock.recv(1024).decode()
            except (ConnectionAbortedError, ConnectionResetError) as E:
                logging.warning(f"The connection with the client {cliSock.getpeername()} has ended: {E}")
                self.closeNext.append(cliSock)
                return
                
            #pdb.set_trace()
            if len(cur_recv) == 0:
                logging.warning(f"Server is not receiving from {cliSock.getpeername()}. Connection is closing!")
                # The data that was sent before an EOMsg was found will be dropped
                self.closeNext.append(cliSock)
                return
            
            data_recv = data_recv + cur_recv
        
        if clientList[2] == "":
            regexResult = self.botnamePattern.search(data_recv)
            if bool(regexResult):
                clientList[2] = regexResult.groups()[0] 
        
        logging.info(f"Data received: {data_recv}")
        msgList = data_recv.replace("\n", "").split(self.endOfMsg)
        self.sendQueues[cliSock.getpeername()][1] = msgList.pop()
        
        for msg in msgList:
            self.populateSendQues(msg, cliSock)
    
    def populateSendQues(self, msg, cliSock):
        self.history.append(msg)
        for key in self.sendQueues.keys():
            if key != cliSock.getpeername():        
                self.sendQueues[key][0].put(msg)
                
    def removeClient(self, cliSock):
        logging.info(f"The connection to {cliSock.getpeername()} is closing.")
        uname = self.sendQueues[cliSock.getpeername()][2]
        self.populateSendQues(f"{uname}: Good bye.\nUser {uname} left the chat.\n", cliSock)
        self.sendQueues.pop(cliSock.getpeername())
        cliSock.close()
        self.checkError.remove(cliSock)
        self.checkReadable.remove(cliSock)
        self.checkWritable.remove(cliSock)
        
        
        
        
            


if __name__=="__main__":
    
    #Handle command line argument
    parser = argparse.ArgumentParser(description="This program starts a sigle threaded chat service.")
    parser.add_argument('-p', '--Port', nargs='?', const=2020, metavar="PORT",
                        type=int, help="The port number associated with the service")
    args = parser.parse_args()
    
    logDay = f"{datetime.datetime.now().date().__str__()}"
    logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s', 
                        filename=f"./Logs/chatServer_{logDay}.log", level=logging.INFO)
    
    server = SimpleChatServer(args.Port)
    server.startService()
    
    