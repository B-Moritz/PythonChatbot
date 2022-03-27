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
    
    The object has three interesting attributes which describes the 
    message: 
        tags - type: python list - Contains tags from the Tags enum class 
                                   that describe the content of the message.
        
        location - type: String - This variable contians a location which 
                                  was identified in the message. If there are 
                                  multiple locations, the first mentioned 
                                  location is picked.
                                  
        username - type: String - This variable contians the username of the 
                                  user which joined the chat. The variable is 
                                  only set if the message is a join message.
    The object has one method:
        classifyMsg() - This message tests the message against some 
                        regular expressions which are defined as constants 
                        and are connected to a certain tag.
    """
    
    complicationDetection = re.compile(".*: .*[\.\?\!\:][A-Za-z0-9\s]+")
    questionWords = re.compile("([Ww]hat)|([Ww]here)|([Ww]hen)|([Ww]hy)|([Ww]hich) \
                               |([Ww]ho)|([Hh]ow)|([Ww]hose)|([cC]an you)|([cC]ould you)|([Ii]s it)|([dD]o you)")

    knownSubjects = {"temperature" : Tags.temperature, "weather" : Tags.weather, "hot" : Tags.temperature, 
                     "cold" : Tags.temperature, "sunny" : Tags.weather, }
    opinions = ["[Dd]o you like", "[Cc]an you rate", "[Pp]lease rate", "[Dd]o you think", "[Hh]ow would you rate"]
    
    locationReg = "{} (.*)[\s\!\.\?\,]|{} (.*)$"
    locationWords = ["[iI]n", "[aA]t"]
    
    regJoinCase = re.compile("User (.*) has joined the chat!")
    
    CONNECTION_STOPED_MSG = "The connection with the chat server has stoped."
        
    def __init__(self, msg):
        
        # input validation
        if type(msg) != str:
            # Verify that the argument given to the method is of the right type
            raise TypeError(f"The argument msg provided to the method was of type {type(msg)}. \
                            Please provide a string as argument!")
                            
        if bool(self.complicationDetection.search(msg)):
            # Verify that the message is not too complicated
            print("TO COMPLICATED: " + str(msg))
            raise ValueError("The provided message is too complicated.\n " +
                             "I can only process one sentence.")
           
        self.msg = msg
        # The message is splitt into a list of words
        self.msgList = self.msg.split(" ")
        
        self.tags = []
        self.location = ""
        self.username = ""
        
    def classifyMsg(self):
        """
        This method classifies the message that was stored in the object.
        It adds tags to the tags attribute. The location attribute is 
        set if a location is detected in the message.

        Returns
        -------
        None.

        """
        # It is first checked if the message is an introduction message 
        # which is received when a new user joined the chat.
        joinMatch = self.regJoinCase.search(self.msg)
        if bool(joinMatch):
            # The message is only taged with the join tag if it is an 
            # introduction.
            self.tags.append(Tags.join)
            self.username = joinMatch.groups()[0]
            # The metod ends to avoid that other tags can be added
            return
        
        # The findall() method of the re module is used to identify question words 
        # in the message.
        self.questionWordsDetected = self.questionWords.findall(self.msg)
        
        if len(self.questionWordsDetected) > 0:
            # Tag the message as question if it contians question words
            self.tags.append(Tags.question)
        else:
            # If the message was not detected as a question, it is classified 
            # as a statement/suggestion
            self.tags.append(Tags.statement)
            
            
        # Find known subjects
        subjects = self.knownSubjects.keys()
        for word in self.msgList:
            # For each word in the message, check if it is in the list of 
            # known subject (subjecs)
            word = word.lower()
            if word in subjects:
                # If the word is a key in the subjects dictionary 
                #  -> add the coresponding tag 
                self.tags.append(self.knownSubjects[word])
            
        # Check if the message askes for an opinion
        for opi in self.opinions:
            curPat = re.compile(opi)
            if bool(curPat.search(self.msg)):
                self.tags.append(Tags.opinion)
                
        # Check for a location
        for word in self.locationWords:
            # For each word in the 
            curPat = re.compile(self.locationReg.format(word, word))
            result = curPat.search(self.msg)
            if result:
                self.tags.append(Tags.location)
                self.location = result.groups()[0]
                break
                

class ChatUser(threading.Thread):
    """
    This class contians method used to connect, send and receive message with 
    the chat service provided by the server.py module.
    """
    # End of message code used to identify the end of each message sent between the server and the user
    END_OF_MSG = "::EOMsg::"
    data_recv = ""
    kickedMessage = re.compile("^Kicked by the host for (.*)")
    
    def __init__(self, dest, port, username):
        threading.Thread.__init__(self)
        
        # Validate the username provided to the constructor
        if type(username) != str:
            raise ValueError(f"The provided username \"{username}\" of type {type(username)} is not valid." + 
                             "Please provide a username as a string")
        # Set the username
        self.username = username
        
        # Instantiate the client socket object
        self.cliSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if type(dest) != str:
            # Validatet that the destination address is a string
            raise ValueError(f"The provided destination address was {type(dest)}. \
                             Pleas provide a string as destination.")
                             
        if type(port) != int:
            # Validate that the destination port is an integer
            raise ValueError(f"The provided port number is of type {type(port)}. \
                             Please provide an integer as port number.")
                       
        # The destination port and address attributes are set
        self.dest = dest
        self.port = port
        
        self.sendQueue = Queue()
        self.recvQueue = Queue()
        self.event = threading.Event()
        
        
    def sendInitialMessage(self, user):
        self.sendQueue.put(f"{user}")
        print(f"\nYou have joined the chat with username {user}!\n\n" + 
              "Loading existing messages in the thread", end="\r")
        
    def run(self):
        try:
            self.cliSock.connect((self.dest, self.port))
        except:
            # Write to terminal if the connection could not be established
            print(f"Unable to connect to the chat server on destination {self.dest} and port {self.port}.")
            return
        socketList = [self.cliSock]
        
        self.sendInitialMessage(self.username)
        
        outputThread = threading.Thread(target=self.generateOutput, daemon=True)
        outputThread.start()
        
        while not self.event.is_set():
            # Run the select command to check if the socket has received any data, 
            # has encountered an error or can send to the server.
            readable, writable, error = select.select(socketList, socketList, socketList, 10) 
            
            if len(readable) > 0 and not self.event.is_set():
                self.receiveFromServer(readable[0])
                
            if len(writable) > 0 and self.sendQueue.qsize() > 0 and not self.event.is_set():
                self.sendToServer(writable[0])
            else:
                # If the socket is not writable, the connection is asumed to be stoped
                #self.event.set()
                time.sleep(1)
                
            for i in range(self.recvQueue.qsize()):
                print("\n" + self.recvQueue.get().replace(self.END_OF_MSG, ""))
                
            if len(error) > 0:
                print(self.CONNECTION_STOPED_MSG)
                self.event.is_set()
            
        
        # The client socket is closed when the while loop is done
        self.cliSock.close()
        # Waiting for the thread for the user interaction to end.
        outputThread.join(1)
        
    def generateOutput(self):
        exitPattern = re.compile("^\/exit")
        while not self.event.is_set():
            msg = input()
            if bool(exitPattern.search(msg)):
                print("You are disconnecting from the chat.")
                self.event.set()
            else:
                print(f"{self.username}: " + msg)
                self.sendQueue.put(msg)
        
        
    def receiveFromServer(self, cliSock):
        pattern = re.compile(self.END_OF_MSG)
        cur_recv = ""
        while not bool(pattern.search(self.data_recv)):
            try:
                cur_recv = cliSock.recv(1024).decode()
            except ConnectionResetError:
                # If the client socket raises the ConnectionResetError 
                # this program implies that the server stoped the connection with this 
                # client.
                print(self.CONNECTION_STOPED_MSG)
                self.initiateClosure()
                return
                
            self.data_recv += cur_recv
            
            if len(cur_recv) == 0:
                # If the socket fetched 0 bytes from the receive buffer, 
                # a disconnected connection is indicated.
                if not self.event.is_set():
                    self.initiateClosure()
                    print(self.CONNECTION_STOPED_MSG)
                return
        
        msgList = self.data_recv.split(self.END_OF_MSG)
        self.data_recv = msgList.pop()
        for msg in msgList:
            curKickedMatch = self.kickedMessage.search(msg) 
            if bool(curKickedMatch):
                # The server has sent a kick message 
                reason = curKickedMatch.groups()[0]
                # The client socket is therefore closed with the reason 
                # given by the server.
                self.initiateClosure(reason if reason else " unknown.")
            else:
                self.recvQueue.put(msg)
                    
            
    def sendToServer(self, cliSock):
        dataSent = 0
        for i in range(self.sendQueue.qsize()):
            curMsg = (f"{self.username}: " + self.sendQueue.get() + self.END_OF_MSG).encode()
            
            while dataSent < len(curMsg) and not self.event.is_set():
                cur_sent = cliSock.send(curMsg[dataSent:])
                
                if cur_sent == 0:
                    print(self.CONNECTION_STOPED_MSG)
                    self.initiateClosure()
                    return
                dataSent += cur_sent
    
    def initiateClosure(self, reason=""):
        self.event.set()
        if reason != "":
            print("\nYou have been removed from the chat by the host. " +
                  f"The following reason was given: {reason}")
        
        
class ChatBot(ChatUser, threading.Thread):
    
    unamePattern = re.compile("^(.*[Bb]ot): |[-]+\[End existing messages\][-]+")
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
    
    greetings =["Hi", "Hello", "Welcome"]
    # Response delay
    BOT_RESPONSE_DELAY = 1
    
    def __init__(self, dest, port, username="Simple_Chat_Bot"):
        ChatUser.__init__(self, dest, port, username)
        
    def run(self):
        #pdb.set_trace()
        try:
            self.cliSock.connect((self.dest, self.port))
        except:
            # Write to terminal if the connection could not be established
            print(f"Unable to connect to the chat server on destination {self.dest} and port {self.port}.")
            return
        
        self.sendInitialMessage(self.username)
        self.sendToServer(self.cliSock)
        while not self.event.is_set():
            
            startTime = time.time()
            while (time.time() - startTime) < self.BOT_RESPONSE_DELAY: 
                self.receiveFromServer(self.cliSock)
                
            self.generateResponse()
            if not self.event.is_set():
                self.sendToServer(self.cliSock)
            
    def initiateClosure(self, reason=""):
        """
        This method initiates the termination of the client socket for the bot.
        
        Parameters
        ----------
        reason : String
            This argument is a string containing the reason for why the server 
            stoped the connection. Because this is a bot, the reason should be "" and
            therefore ignored.
        """
        # The event flag is set in order to break the while loop in the main thread 
        self.event.set()
        print(f"{self.username} is disconnected!")
        
        
    def sendInitialMessage(self, botName):
        """
        This method adds the botname to the send queue. 

        Parameters
        ----------
        botName : String
            The name of the bot which is joining the chat thread.
        """
        self.sendQueue.put(f"{botName}")
            
    def generateResponse(self):
        """
        This method generates the response to the last received message.
        If there are several messages in the receive queue for the client, 
        all messages except the latest will be ignored. The method then 
        executes the analysis of the message with the MsgAnalysis class and 
        adds a response message to the send queue.
        
        The method calls the getBotResponse method in order to get the specific 
        bot. The getBotResponse should be overwritten for each bot that inherits 
        the ChatBot classs. This way the response can be customized for each bot.
        """
        curMsg = ""
        while self.recvQueue.qsize() > 0:
            # If the receive queue contains more than one message, 
            # then all messages are dropped except one (the latest replyable message)
            msg = self.recvQueue.get()
            
            if not bool(self.unamePattern.search(msg)):
                # The message that will be replyed to by the bot is set as curent message
                # if it is not from a bot.
                curMsg = msg
        
        if curMsg:
            # If the there is a current message set then generate a reply.
            # else return without any response generated.
            try:
                msgObj = MsgAnalysis(curMsg)
            except ValueError as E:
                # If the messag cannot be handeled by the analysis class, 
                # then send the exception as a message.
                self.sendQueue.put(str(E))
                return
            # Call the classify method to add tags to the message
            msgObj.classifyMsg()
            
            if Tags.join in msgObj.tags:
                # If the message is taged as join message then add a 
                # greeting and return.
                if not msgObj.username[-3:].lower() == "bot":
                    # If the join message is related to a bot, then no greeting is sent.
                    self.sendQueue.put(random.choice(self.greetings) + " " + 
                                       msgObj.username + random.choice(["!", ".", ""]))
                #print(f"Greeting because of: {curMsg}") # Used for debuging
            else: 
                # Get the specific response for the bot 
                response = self.getBotResponse(msgObj)
                # Send the response
                self.sendQueue.put(response)
            
    def getBotResponse(self, msgObj):
        """
        This method is finding a simple response to a message. The method 
        takes an MsgAnalysis object as argument.
        
        Parameters
        ----------
        msgObj : MsgAnalysis
            An object with the message that should be responded to.
            The object should contian the result of classsification process
            (see docstring of MsgAnalysis). 

        Returns
        -------
        The method returns a string, which is the response to the message in 
        the provided MsgAnalysis object.

        """
        if Tags.question in msgObj.tags:
            # Is the message a question?
            if Tags.opinion in msgObj.tags:
                # If the message is a request for an opinion, then 
                # return a random response for opinion questions
                return(random.choice(self.opinionResponses))
            elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                # If the message is asking for the temperature or the weather 
                # then return a random weather response
                return(random.choice(self.weatherResponse))
            elif Tags.location in msgObj.tags:
                # If the question only contians a location then 
                # Return a random location response.
                return(random.choice(self.locationResponse))
                
        elif Tags.statement in msgObj.tags:
            # Is the message a statement/suggestion?
            # A random statement response is returned.
            return(random.choice(self.statementResponses))
        else:
            # General response
            return(random.choice(self.generalResponse))
                
                
class WeatherBot(ChatBot):
    """
    This class contians the methods for the Weatherbot. It inherits from 
    the ChatBot class. The bot can be used by first instantiating an object. 
    The destination address and port should be given as argumen to the constructor.
    The object will be a threading object and the thread can be started with the
     method start(). The method initiateClosure can be called to stop the bot.
    """
    unknownLocation = ["Please name a known city!", "What city are you refering too?"]
    
    def __init__(self, dest, port, username="Weather_Bot"):
        ChatBot.__init__(self, dest, port, username)
        self.YrObj = yr.WeatherApi()
                
    def getBotResponse(self, msgObj):
        """
        This method geterates a response to the message provided as argument.
        The response is specific for the Weatherbot. 

        Parameters
        ----------
        msgObj : MsgAnalysis
            An object with the message that should be responded to.
            The object should contian the result of classsification process
            (see docstring of MsgAnalysis). 

        Returns
        -------
        The method returns a string, which is the response to the message in 
        the provided MsgAnalysis object.

        """
        if Tags.question in msgObj.tags:
            # Is the message a question?
            #print("Question identified") # Used for debug
            if Tags.opinion in msgObj.tags:
                # Is the message asking for an opinion?
                #print("Opinion identified") #Used for Debug
                
                if Tags.weather in msgObj.tags and Tags.location in msgObj.tags:
                    # Does the message contain weather subjects and a location?
                    #print("Weather and location identified") # Used for debug
                    try:
                        # Get weather data for the specified location
                        airTemp, cloudAreaFrac = self.YrObj.getCurrentWeatherData(msgObj.location)
                        # Add message about the weather for the given location
                        return("The weather in " + msgObj.location + 
                                           " is " + self.YrObj.convertCloudArea(cloudAreaFrac) + 
                                           " and " + self.YrObj.convertTemperature(airTemp) + ". " + 
                                           ("I like it!" if airTemp > 15 and cloudAreaFrac < 10 else "I do not like it!") + 
                                           "\n Information is based on data from MET Norway.")
                                            # The bot likes the weather if air temperature is greater than 15 and 
                                            # cloud area fraction is less than 10 %.
                        
                    except ValueError:
                        #print("City not found in list") # Used for debug
                        # The location was not identified as a city.
                        return(random.choice(self.unknownLocation))
                elif Tags.weather in msgObj.tags:
                    #print("weather but no location was identified") # Used for debug
                    # The location was not identified.
                    return(random.choice(self.unknownLocation))
                else:
                    #print("general opinion response") # Used for debug
                    # General response for opinion questions
                    return(random.choice(self.opinionResponses))
                    
            elif Tags.temperature in msgObj.tags:
                # Is the message about the temperature?
                #print("Temperature identified") # Used for debug
                if Tags.location in msgObj.tags:
                    # Is the message containing a location?
                    #print("Location identified") # Used for debug
                    try:
                        # Get the weather data for the location
                        self.YrObj.getCurrentWeatherData(msgObj.location)
                        # Send a message informing about the temperature for the next hour.
                        return("The temperature in " + msgObj.location + 
                                           " is " + str(self.YrObj.curData['Air temperature']) 
                                           + " degree celcius!" + 
                                           "\n Information is based on data from MET Norway.")
                    except ValueError:
                        #print("City not found in list") # Used for debug
                        # The location was not identified as a city.
                        return(random.choice(self.unknownLocation))
                else:
                    #print("weather but no location was identified") # Used for debug
                    # The location was not identified.
                    return(random.choice(self.unknownLocation))
                    
            elif Tags.weather in msgObj.tags:
                #print("weather was identified") # Used for debug
                # Is the message askin for the wether?
                if Tags.location in msgObj.tags:
                    #print("Location identified") # Used for debug
                    try:
                        # Get the weather data for the given location
                        self.YrObj.getCurrentWeatherData(msgObj.location)
                        # Send a message about the weather at the given location the next hour.
                        return("The temperature in " + msgObj.location + 
                                          " is " + str(self.YrObj.curData['Air temperature']) +
                                          " degree celcius! The sky is " + 
                                          str(self.YrObj.convertCloudArea(self.YrObj.curData['Cloud_area_fraction'])) + 
                                          ".\n This information is based on data from MET Norway.")
                                           
                    except ValueError:
                        #print("Location was not found in list") # Used for debug
                        # The location was not identified as a city.
                        return(random.choice(self.unknownLocation))
                         
        elif Tags.statement in msgObj.tags:
            #print("identified as statement/suggestion")
            return(random.choice(self.statementResponses))
        else:
            # If the message is not a statement or a question, reply with general response
            return(random.choice(self.generalResponse))
                        
            
if __name__ == "__main__":
    # Instantiate an argument parser to handle the commandline arguments and creating a help message.
    parser = argparse.ArgumentParser(description="This program starts all chatbots defined, " + 
                                     "including a user client, and connects them to the server.")
    # Adding a commandline parameter -d for the destination address. The user can provide an address to the 
    # chat server as a string.
    parser.add_argument("-d", "--Dest", nargs='?', default=socket.gethostbyname(socket.gethostname())
                        , metavar="DESTINATION", type=str, help="The IPv4 address of the server")
    # Adding a commandline parameter for the destination port. 
    parser.add_argument("-p", "--Port", nargs='?', default=2020, metavar="PORT", type=int, 
                        help="Portnumber that the server is listening on.")
    # Adding a commandline paramter to add a curstom username to the user client. The default value is "Chat_User"
    parser.add_argument("-u", "--Username", nargs='?', default="Chat_User", metavar="USERNAME", type=str, 
                        help="Username displayed with messages sent from the client.")
    
    argParsed = parser.parse_args()
    # Create a thread for the client user connection
    testChat = ChatUser(argParsed.Dest, argParsed.Port, argParsed.Username)
    testChat.start()
    
    # time.sleep(4)
    # # Start a simple chat bot.
    # testBot = ChatBot(argParsed.Dest, argParsed.Port)
    # testBot.start()
    
    # time.sleep(2)
    # # Start the weatherBot. 
    # weatherBot = WeatherBot(argParsed.Dest, argParsed.Port)
    # weatherBot.start()
    
    testChat.join()
    # Stop all bots if the client thread is finished
    # if testBot.is_alive():
    #     testBot.initiateClosure()
    # testBot.join()
    
    # if weatherBot.is_alive():
    #     weatherBot.initiateClosure()
        
    # weatherBot.join()
    
    