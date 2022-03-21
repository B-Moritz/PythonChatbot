# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 16:38:50 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

This module, client, is part of the solution to the individual 
portofolio assignment in the course DATA2410 - Datanetverk og 
skytjenester. This module contians classes used to connect chat 
users and bots to a single thread chat, hosted on a server.

If this file, client.py, is executed with  
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
import pdb
import YrInterface as yr

class Tags(enum.Enum):
    """
    This class is a python enum class consisting of the different 
    tags that a message, provided to an MsgAnalysis object, can be taged with.
    """
    #If a message is classified as question, it could contain one of the question words.
    question = 1
    #If the message is not a question, it is treated as a statement.
    statement = 2
    #If the message contains the word temperature it is classified as temperature message
    temperature = 3
    #If the message contains the word weather
    weather = 4
    #If the message asks for a location (question classification is required)
    location = 5
    #If the message is a question and contains words that requests an opinion
    opinion = 6
    #If the message contains a city
    city = 7
    #If the message is a join message
    join = 8
    

class MsgAnalysis:
    """
    This class contians functions for analysing messages received 
    through the chat client. The ChatUser class and its subclasses 
    (chatbots) are dependant on this class. It is used to 
    classify/tag messages received.
    
    The object has two interesting attributes which describes the 
    message: 
        tags - type: python list - Contains tags from the Tags enum class 
                                   that describe the content of the message.
        
        location - type: string - This variable contians a location which 
                                  was identified in the message. If there are 
                                  multiple locations, the first mentioned 
                                  location is picked.
                                  
    The object has one method:
        classifyMsg() - This message tests the message against some 
                        regular expressions which are defined as constants 
                        and are connected to a certain tag.
    """
    
    complicationDetection = re.compile("[\.\?\!\:][A-Za-z0-9\s]+")
    questionWords = re.compile("([Ww]hat)|([Ww]here)|([Ww]hen)|([Ww]hy)|([Ww]hich) \
                               |([Ww]ho)|([Hh]ow)|([Ww]hose)|([cC]an you)|([cC]ould you)|([Ii]s it)")

    knownSubjects = {"temperature" : Tags.temperature, "weather" : Tags.weather, "hot" : Tags.temperature, 
                     "cold" : Tags.temperature, "sunny" : Tags.weather, }
    opinions = ["do you like", "can you rate", "please rate", "do you think"]
    
    locationReg = "{} (.*)[\s\!\.\?\,]|{} (.*)$"
    locationWords = ["[iI]n", "[aA]t", "[fF]or"]
    
    regJoinCase = re.compile("User .* has joined the chat!")
    
    tags = []
    location = ""
    
    def __init__(self, msg):
        
        # input validation
        if type(msg) != str:
            # Verify that the argument given to the method is of the right type
            raise TypeError(f"The argument msg provided to the method was of type {type(msg)}. \
                            Please provide a string as argument!")
                            
        if bool(self.complicationDetection.search(msg)):
            # Verify that the message is not too complicated
            raise ValueError("The provided message is too complicated.\n \
                             Class MsgAnalysis can only process one simple sentence.")
           
        self.msg = msg
        
    def classifyMsg(self):
        """
        This method classifies the message that was stored in the object. 

        Returns
        -------
        None.

        """
        # It is first checked if the message is an introduction message 
        # which is received when a new user joined the chat.
        if bool(self.regJoinCase.search(self.msg)):
            # The message is only taged with the join tag if it is an 
            # introduction.
            self.tags.append(Tags.join)
            # The metod ends to avoid that other tags can be added
            return
        
        # The message is splitt into a list of words
        self.msgList = self.msg.split(" ")
        # The findall() method of the re module is used to identify question words 
        # in the message.
        self.questionWordsDetected = self.questionWords.findall(self.msg)
        # If there are question words in the 
        if len(self.questionWordsDetected) > 0:
            self.tags.append(Tags.question)
            if "where" in self.questionWordsDetected or "where" in self.questionWordsDetected:
                self.tags.append(Tags.location)
        else:
            self.tags.append(Tags.statement)
            
        #Find known subjects
        subjects = self.knownSubjects.keys()
        for word in self.msgList:
            word = word.lower()
            if word in subjects:
                self.tags.append(self.knownSubjects[word])
            
        # Check if the message askes for an opinion
        for opi in self.opinions:
            curPat = re.compile(opi)
            if bool(curPat.search(self.msg)):
                self.tags.append(Tags.opinion)
                
        # Check for a location
        for word in self.locationWords:
            curPat = re.compile(self.locationReg.format(word, word))
            result = curPat.search(self.msg)
            if result:
                self.tags.append(Tags.location)
                self.location = result.groups()[1]
                

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
        
        
    def sendInitialMessage(self, user):
        self.sendQueue.put(f"\nUser {user} has joined the chat!\n")
        print(f"\nUser {user} has joined the chat!\n")
        
    def run(self):
        self.cliSock.connect((self.dest, self.port))
        socketList = [self.cliSock]
        threadList = []
        
        self.sendInitialMessage(self.botName)
        
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
                print(f"\n{self.botName} is disconnecting from the chat\n")
                self.event.set()
            else:
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
    
    weatherResponse = ["I do not want to talk about the weather. It is boring and always depressing!", 
                      "I have the same question.", 
                      "If you want to talk about the weather, you have to talk to someone else."]
    
    locationResponse = ["I am not an expert in geography unfortunatly, \
                        maybe some one else can help with this?"]
    
    generalResponse = ["I am not sure if I understand your message.\n Could you please clarify?",
                       "Please write in english, so I can understand you!"]
    
    greetings =["Hi", "Hello", "Welcome!"]
    
    
    def __init__(self, dest, port):
        ChatUser.__init__(self, dest, port)
        
    def run(self):
        
        self.cliSock.connect((self.dest, self.port))
        self.sendInitialMessage(self.botName)
        self.sendToServer(self.cliSock)
        #pdb.set_trace()
        while not self.event.is_set():
            self.receiveFromServer(self.cliSock)
            self.generateResponse()
            self.sendToServer(self.cliSock)
            
    def initiateClosure(self):
        self.event.set()
        print(f"{self.botName} is disconnected!")
        
    def sendInitialMessage(self, user):
        self.sendQueue.put(f"\nUser {user} has joined the chat!\n")
            
    def generateResponse(self):
        
        while self.recvQueue.qsize() > 1:
            # If the receive queue contains more than one message, 
            # then all messages are dropped except one (the latest)
            self.recvQueue.get()
        
        
        curMsg = self.recvQueue.get()
        if not bool(self.unamePattern.search(curMsg)):
            # if the message is not from a bot
            try:
                msgObj = MsgAnalysis(curMsg)
            except ValueError as E:
                self.sendQueue(E)
                return
            
            msgObj.classifyMsg()
            
            if Tags.join in msgObj.tags:
                self.sendQueue.put(random.choice(self.greetings))
                return
            
            if Tags.question in msgObj.tags:
                
                if Tags.opinion in msgObj.tags:
                    self.sendQueue.put(random.choice(self.opinionResponses))
                elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                    self.sendQueue.put(random.choice(self.weatherResponse))
                elif Tags.location in msgObj.tags:
                    self.sendQueue.put(random.choice(self.locationResponse))
                    
            elif Tags.statement in msgObj.tags:
                self.sendQueue.put(random.choice(self.statementResponses))
        
            else:
                self.sendQueue.put(random.choice(self.generalResponse))
                
                
class WeatherBot(ChatBot):
    botName = "Weather_Bot"
    
    unknownLocation = ["Please name a known city!", "What city are you refering too?"]
    
    
    def __init__(self, dest, port):
        ChatBot.__init__(self, dest, port)
        self.YrObj = yr.weatherAPI()
        
                
    def generateResponse(self):
        while self.recvQueue.qsize() > 1:
            # If the receive queue contains more than one message, 
            # then all messages are dropped except one (the latest)
            self.recvQueue.get()
        # The last message is set as the message to be handled by the bot    
        curMsg = self.recvQueue.get()
        
        if not bool(self.unamePattern.search(curMsg)):
            # if the message is not from a bot
            
            # The message is analyzed by instantiating an analysis object 
            # and running the classification method 
            try:
                msgObj = MsgAnalysis(curMsg)
            except ValueError as E:
                self.sendQueue(E)
                return
            msgObj.classifyMsg()
            
            if Tags.join in msgObj.tags:
                self.sendQueue.put(random.choice(self.greetings))
                return
            
            if Tags.question in msgObj.tags:
                # Is the message a question?
                if Tags.opinion in msgObj.tags:
                    # Is the message asking for an opinion?
                    if Tags.weather in msgObj.tags and Tags.location in msgObj.tags:
                        try:
                            self.YrObj.getCurrentWeatherData(msgObj.location)
                            self.sendQueue.put(f"The weather in {msgObj.location} is \
                                               {self.YrObj.classifyCloadArea()} and \
                                               {self.YrObj.classifyTemperature()}!")
                        except ValueError:
                            # The location was not identified as a city.
                            self.sendQueue.put(random.choice(self.unknownLocation))
                    else:
                        # The location was not identified.
                        self.sendQueue.put(random.choice(self.unknownLocation))
                        
                elif Tags.temperature in msgObj.tags:
                    # Is the message about the temperature?
                    if Tags.location in msgObj.tags:
                        try:
                            self.YrObj.getCurrentWeatherData(msgObj.location)
                            self.sendQueue.put(f"The temperature in {msgObj.location} \
                                               is {self.YrObj.curData['Air temperature']} degree celcius! \
                                               Based on data from MET Norway.")
                        except ValueError:
                            # The location was not identified as a city.
                            self.sendQueue.put(random.choice(self.unknownLocation))
                    else:
                        # The location was not identified.
                        self.sendQueue.put(random.choice(self.unknownLocation))
                        
                elif Tags.weather in msgObj.tags:
                    # Is the message askin about the wether?
                    if Tags.location in msgObj.tags:
                        try:
                             self.YrObj.getCurrentWeatherData(msgObj.location)
                             self.sendQueue.put(f"The temperature in {msgObj.location} \
                                                is {self.YrObj.curData['Air temperature']} \
                                                degree celcius! The sky is {self.YrObj.classifyCloadArea()}. \
                                                Based on data from MET Norway.")
                                                
                        except ValueError:
                            # The location was not identified as a city.
                            self.sendQueue.put(random.choice(self.unknownLocation))
                             
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
    testChat.start()
    
    time.sleep(4)
    testBot = ChatBot(argParsed.Dest, argParsed.Port)
    testBot.start()
    
    #time.sleep(2)
    #weatherBot = WeatherBot(argParsed.Dest, argParsed.Port)
    #weatherBot.start()
    
    testChat.join()
    testBot.initiateClosure()
    #weatherBot.initiateClosure()
    testBot.join()
    #weatherBot.join()
    
    