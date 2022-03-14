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
#import select


class ChatBot(threading.Thread):
    sendQueue = Queue()
    recvQueue = Queue()
    event = threading.Event()
    endOfMsg = "::EOMsg::"
    botName = "Userchat"
    
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
        
        recvThread = threading.Thread(target=self.receiveFromServer, args=(self.cliSock, ))
        recvThread.start()
        
        sendThread = threading.Thread(target=self.sendToServer, args=(self.cliSock, ))
        sendThread.start()
        
        outputThread = threading.Thread(target=self.generateOutput)
        outputThread.start()
        
        while not self.event.is_set():
            
            for i in range(self.recvQueue.qsize()):
                print("\n" + self.recvQueue.get().replace(self.endOfMsg, "\n"))
            
            time.sleep(1)
        
        self.cliSock.close()
        print("Socket closed")
        outputThread.join()
        print("outputThread has finished!")
        recvThread.join()
        print("recvThread has finished!")
        sendThread.join()
        print("sendThread has finished!")
        print("returning")
        return
        
    def generateOutput(self):
        pattern = re.compile(f"^{self.botName}: \/exit")
        while not self.event.is_set():
            msg = f"{self.botName}: " + input()
            pdb.start()
            if bool(pattern.search(msg)):
                print(f"\n{self.botName} is disconnecting from chat\n")
                self.event.set()
            
            print(msg + "\n")
            self.sendQueue.put(msg + self.endOfMsg)
        
        
    def receiveFromServer(self, cliSock):
        pattern = re.compile(self.endOfMsg)
        data_recv = ""
        cur_recv = ""
        while not self.event.is_set():
            cur_recv = cliSock.recv(1024).decode()
            data_recv += cur_recv
            
            if len(cur_recv) == 0:
                print(f"Connection to {cliSock.getpeername()} is corrupted.")
                self.event.set()
                return
            elif bool(pattern.search(data_recv)):
                msgList = data_recv.split(self.endOfMsg)
                data_recv = msgList.pop()
                for msg in msgList:
                    self.recvQueue.put(msg)
                    
            
    def sendToServer(self, cliSock):
        
        while not self.event.is_set():
            dataSent = 0
            for i in range(self.sendQueue.qsize()):
                curMsg = self.sendQueue.get().encode()
                
                while dataSent < len(curMsg):
                    cur_sent = cliSock.send(curMsg[dataSent:])
                    
                    if cur_sent == 0:
                        print(f"Connection to {cliSock.getpeername()} is corrupted.")
                        self.event.set()
                        return
                    dataSent += cur_sent
            
            time.sleep(2)
        
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This program starts all chatbots defined and connects \
                                     them to the server")
                                     
    parser.add_argument("-d", "--Dest", nargs='?', const=socket.gethostbyname(socket.gethostname())
                        , metavar="DESTINATION", type=str, help="The IPv4 address of the server")
    
    parser.add_argument("-p", "--Port", nargs='?', const=2020, metavar="PORT", type=int, help="Portnumber that the server is listening on.")
    argParsed = parser.parse_args()
    
    testChat = ChatBot(argParsed.Dest, argParsed.Port)
    testChat.run()
    
    