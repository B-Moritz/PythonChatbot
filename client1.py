# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 16:38:50 2022

@author: b-mor
"""

import socket
#import WetherAPI
import argparse
import re
import threading
from queue import Queue
import time
import pdb
import select


class ChatBot(threading.Thread):
    sendQueue = Queue()
    recvQueue = Queue()
    event = threading.Event()
    endOfMsg = "::EOMsg::"
    botName = "Userchat"
    data_recv = ""
    
    def __init__(self, dest, port):
        threading.Thread.__init__(self)
        
        self.cliSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if type(dest) != str:
            raise ValueError(f"The provided destination address was {type(dest)}. \
                             Pleas provide a string as destination.")
                             
        if type(port) != int:
            raise ValueError(f"The provided port number is of type {type(port)}. \
                             Please provide an integer as port number.")
                             
        self.dest = dest
        self.port = port
        
    def run(self):
        self.cliSock.connect((self.dest, self.port))
        socketList = [self.cliSock]
        threadList = []
        
        outputThread = threading.Thread(target=self.generateOutput)
        outputThread.start()
        
        while not self.event.is_set():
            
            readable, writable, error = select.select(socketList, socketList, socketList, 10) 
            
            if len(readable) > 0:
                recvThread = threading.Thread(target=self.receiveFromServer, args=(readable[0], ))
                recvThread.start()
                threadList.append(recvThread)
                
            if len(writable) > 0 and self.sendQueue.qsize():
                sendThread = threading.Thread(target=self.sendToServer, args=(writable[0], ))
                sendThread.start()
                threadList.append(sendThread)
            else:
                time.sleep(1)
                
            for thread in threadList:
                thread.join()
                
            for i in range(self.recvQueue.qsize()):
                print("\n" + self.recvQueue.get().replace(self.endOfMsg, "\n"))
                
            if len(error) > 0:
                print("Error with the connection to the server. The connection is closing.")
                self.event.is_set()
            
        
        
        self.cliSock.close()
        outputThread.join()
        return
        
    def generateOutput(self):
        pattern = re.compile(f"^{self.botName}: \/exit")
        while not self.event.is_set():
            msg = f"{self.botName}: " + input()
            #pdb.set_trace()
            if bool(pattern.search(msg)):
                print(f"\n{self.botName} is disconnecting from chat\n")
                self.event.set()
            
            print(msg + "\n")
            self.sendQueue.put(msg + self.endOfMsg)
        
        
    def receiveFromServer(self, cliSock):
        pattern = re.compile(self.endOfMsg)
        cur_recv = ""
        while not bool(pattern.search(self.data_recv)):
            try:
                cur_recv = cliSock.recv(1024).decode()
            except ConnectionResetError:
                print("The server stopped the connection.")
                self.initiateClosure()
                return
                
            self.data_recv += cur_recv
            
            if len(cur_recv) == 0:
                print(f"Connection to {cliSock.getpeername()} is corrupted.")
                self.initiateClosure()
                return
        
        msgList = self.data_recv.split(self.endOfMsg)
        self.data_recv = msgList.pop()
        for msg in msgList:
            self.recvQueue.put(msg)
                    
            
    def sendToServer(self, cliSock):
        dataSent = 0
        for i in range(self.sendQueue.qsize()):
            curMsg = self.sendQueue.get().encode()
            
            while dataSent < len(curMsg):
                cur_sent = cliSock.send(curMsg[dataSent:])
                
                if cur_sent == 0:
                    print(f"Connection to {cliSock.getpeername()} is corrupted.")
                    self.initiateClosure()
                    return
                dataSent += cur_sent
    
    def initiateClosure(self):
        self.event.set()
        print("Please press enter to stop the program!")
        
        
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This program starts all chatbots defined and connects \
                                     them to the server")
                                     
    parser.add_argument("-d", "--Dest", nargs='?', const=socket.gethostbyname(socket.gethostname())
                        , metavar="DESTINATION", type=str, help="The IPv4 address of the server")
    
    parser.add_argument("-p", "--Port", nargs='?', const=2020, metavar="PORT", type=int, help="Portnumber that the server is listening on.")
    argParsed = parser.parse_args()
    
    testChat = ChatBot(argParsed.Dest, argParsed.Port)
    testChat.run()
    
    