# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 16:38:50 2022

@author: b-mor
"""

import socket
import argparse
import re
import threading
from queue import Queue
import time
import select
import enum
import random

class Tags(enum.Enum):
    #If a message is classified as question, it could contain one of the question words.
    question = 1
    #If the message is not a question, it is treated as a statement.
    statement = 2
    #If the message contains the word temperature it is classified as temperature message
    temperature = 3
    #If the message contains the word wether
    wether = 4
    #If the message asks for a location (question classification is required)
    location = 5
    #If the message is a question and contains words that requests an opinion
    opinion = 6
    

class MsgAnalysis:
    punctuationDetection = re.compile("([\.\?\!\:])")
    questionWords = re.compile("([Ww]hat)|([Ww]here)|([Ww]hen)|([Ww]hy)|([Ww]hich) \
                               |([Ww]ho)|([Hh]ow)|([Ww]hose)|([cC]an you)|([cC]ould you)")

    tags = []
    knownSubjects = {"temperature" : Tags.temperature, "wether" : Tags.wether}
    opinion = ["like", "rate"] 
    
    def __init__(self, msg):
        self.punctation = self.punctationDetection.findall(msg)
        if type(msg) != str and len(self.punctation) > 1:
            raise ValueError("The provided message is too complicated.\n \
                             Class MsgAnalysis can only process one simple sentence.")
                             
        self.msg = msg
        
    def classifyMsg(self):
        self.msgList = self.msg.split(" ")
        self.questionWordsDetected = self.questionWords.findall(self.msg)
        
        if (self.questionWordDetected) > 0:
            self.tags += Tags.question
            if "where" in self.questionWordsDetected or "where" in self.questionWordsDetected:
                self.tags += Tags.location
        else:
            self.tags += Tags.statement
            
        #Find known subjects
        subjects = self.knownSubjects.keys()
        for word in self.msgList:
            word = word.lower()
            if word in subjects:
                self.tags += self.knownSubjects[word]
            
        
            
        
            

class ChatUser(threading.Thread):
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
        pattern = re.compile("^\/exit")
        while not self.event.is_set():
            msg = input()
            #pdb.set_trace()
            if bool(pattern.search(msg)):
                print(f"\n{self.botName} is disconnecting from chat\n")
                self.event.set()
            
            print(f"\n{self.botName}: " + msg + "\n")
            self.sendQueue.put(msg)
        
        
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
            curMsg = (f"{self.botName}: " + self.sendQueue.get() + self.endOfMsg).encode()
            
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
        
        
class ChatBot(ChatUser, threading.Thread):
    botName = "Simple_Chat_Bot"
    unamePattern = re.compile("^(.*[Bb]ot): ")
    opinionResponses = ["I think it is nice!", 
                        "I am not sure, try to ask someone else.", 
                        "I do not like it."]
    
    statementResponses = ["If you say so!", 
                          "I did not know that.", 
                          "How can you say something like that."]
    
    wetherResponse = ["I do not want to talk about the wether. It is boring and always depressing!", 
                      "I have the same question.", 
                      "If you want to talk about the wether, you have to talk to someone else."]
    
    locationResponse = ["I am not an expert in geography unfortunatly, maybe some one else can help with this?"]
    
    generalResponse = ["I am not sure if I understand your message.\n Could you please clarify?",
                       "Plesae write in english so I can understand you!"]
    
    def __init__(self, dest, port):
        ChatUser.__init__(self, dest, port)
        threading.Thread.__init__(self)
        
    def run(self):
        self.cliSock.connect((self.dest, self.port))
        
        while not self.event.is_set():
            self.receiveFromServer(self.cliSock)
            self.generateResponse()
            self.sendToServer(self.cliSock)
            
    def initiateClosure(self):
        self.event.set()
        print(f"{self.botName} is disconnected!")
            
    def generateResponse(self):
        
        while not self.recvQueue.empty():
            curMsg = self.recvQueue.get()
            if len(self.unamePattern.search(curMsg).groups()) > 0:
                #Do not respond to bots
                continue
            else: 
                msgObj = MsgAnalysis(curMsg)
                
                if Tags.question in msgObj.tags:
                    
                    if Tags.opinion in msgObj.tags:
                        self.sendQueue.put(random.choice(self.opinionResponses))
                    elif Tags.temperature in msgObj.tags or Tags.wether in msgObj.tags:
                        self.sendQueue.put(random.choice(self.wetherResponse))
                    elif Tags.location in msgObj.tags:
                        self.sendQueue.put(random.choice(self.locationResponse))
                        
                elif Tags.statement in msgObj.tags:
                    self.sendQueue.put(random.choice(self.statementResponses))
            
                else:
                    self.sendQueue.put(random.choice(self.generalResponse))
                    

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This program starts all chatbots defined and connects \
                                     them to the server")
                                     
    parser.add_argument("-d", "--Dest", nargs='?', const=socket.gethostbyname(socket.gethostname())
                        , metavar="DESTINATION", type=str, help="The IPv4 address of the server")
    
    parser.add_argument("-p", "--Port", nargs='?', const=2020, metavar="PORT", type=int, help="Portnumber that the server is listening on.")
    argParsed = parser.parse_args()
    
    testChat = ChatUser(argParsed.Dest, argParsed.Port)
    testChat.run()
    
    testBot = ChatBot(argParsed.Dest, argParsed.Port)
    testBot.run()
    
    testChat.join()
    testBot.event.set()
    testBot.join()
    
    