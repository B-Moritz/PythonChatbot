# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 16:38:50 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

This module is part of the solution to the individual 
portofolio assignment in the course DATA2410 - Datanettverk og 
skytjenester. This module contains classes used to connect chat 
users and bots to a single thread chat, hosted on a server.

If this file, client.py, is executed with  
"""

# The socket module 
import socket
import select
# The module used to parse commandline arguments
# https://docs.python.org/3/library/argparse.html#const
import argparse
# Regex library
import re
# Module for working with trheads
import threading
# Thread-safe queue datastructure
from queue import Queue

# Module for working with time and sleep
import time
# The enum class is imported:
    #https://www.geeksforgeeks.org/enum-in-python/
import enum
# Importing the random module used to pick a random message for the host bot
import random

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
    
    # activity tags
    activity = 11
    # If the message si about sport
    sport = 12
    # If the message is about art
    art = 13
    # The message contains a request or suggestion for an activity
    requestActivity = 14
    

class MsgAnalysis:
    """
    This class contians functions for analysing messages received 
    through the chat client. The ChatUser class and its subclasses 
    (chatbots) are dependant on this class. It is used to 
    classify/tag messages received.
    
    The object has four interesting attributes which describes the 
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
                                  
        Activity - type: String - This variable describes the activity found 
                                  to be associated with the message. It is 
                                  only set if the message contains one of 
                                  words in the activityOpinions dictionary.
                                  
    The object has one method:
        classifyMsg() - This message tests the message against some 
                        regular expressions which are defined as constants 
                        and are connected to a certain tag.
    """
    
    # Regex pattern used to detect messages which are too complicated. 
    # A message is for example too complicated if it contains several sentences.
    complicationDetection = re.compile(".*: .*[\.\?\!\:][A-Za-z0-9\s]+")
    # A regex pattern used to determine if the message is asking a question.
    questionWords = re.compile("([Ww]hat)|([Ww]here)|([Ww]hen)|([Ww]hy)|([Ww]hich) \
                               |([Ww]ho)|([Hh]ow)|([Ww]hose)|([cC]an you)|([cC]ould you)|([Ii]s it)|([dD]o you)|([wW]ould you)")
                               
    # Words about the weather maped to their coresponding tags
    weatherSubjects = {"temperature" : Tags.temperature, "weather" : Tags.weather, "hot" : Tags.temperature, 
                     "cold" : Tags.temperature, "sunny" : Tags.weather}
    
    # List of regex strings used to determine if the messages makes a sugestion for an activity
    requestActivities = ["[wW]e could", "[wW]e should", "[cC]an we", "[cC]ould we"]
    
    # Activity words maped to their coresponding tags
    activitiesOpinion = {"sport" : Tags.sport, "art" : Tags.art, "football" : Tags.sport, "tennis" : Tags.sport, 
                         "draw" : Tags.art, "drawing" : Tags.art, "paint" : Tags.art, "painting" : Tags.art}
    
    # List of regex strings used to determine if the message asks for an opinion.
    opinions = ["[Dd]o you like", "[Cc]an you rate", "[Pp]lease rate", "[Dd]o you think", "[Hh]ow would you rate", "What do you think about"]
    
    # List of regex string used to detect locations
    locationWords = ["[iI]n", "[aA]t"]
    # The strings in locationWords are substituted in this regex string.
    # It finds the word refering to a location
    locationReg = "{} (.*)[\s\!\.\?\,]|{} (.*)$"
    
    # Regex pattern used to detect join messages
    regJoinCase = re.compile("User (.*) has joined the chat!")
    
        
    def __init__(self, msg):
        
        # input validation
        if type(msg) != str:
            # Verify that the argument given to the method is of the right type
            raise TypeError(f"The argument msg provided to the method was of type {type(msg)}. \
                            Please provide a string as argument!")
                            
        if bool(self.complicationDetection.search(msg)):
            # Verify that the message is not too complicated
            raise ValueError("The provided message is too complicated.\n " +
                             "I can only process one sentence.")
           
        self.msg = msg
        # The message is splitt into a list of words
        self.msgList = msg.replace(".", "").replace("!", "").replace("?", "").split(" ")
        
        self.tags = []
        self.location = ""
        self.username = ""
        self.activity = ""
        
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
        subjects = self.weatherSubjects.keys()
        activities = self.activitiesOpinion.keys()
        for word in self.msgList:
            # For each word in the message, check if it is in the list of 
            # known subject (subjecs)
            word = word.lower()
            if word in subjects:
                # If the word is a key in the subjects dictionary 
                #  -> add the coresponding tag 
                self.tags.append(self.weatherSubjects[word])
            
            if word in activities:
                # If the word is in the activitiesOpinion dictionary, 
                # then add the activity found to the activity attribute.
                self.activity = word
                # Add the tag associated with the word and add the activity
                self.tags.append(self.activitiesOpinion[word])
                # Add the activity tag
                self.tags.append(Tags.activity)
        
        # Check if the message requests an activity 
        if Tags.activity in self.tags:
            # A request for activity must already have the activity tag.
            for pattern in self.requestActivities:
                # For each request pattern compile and make the serarch
                patternObj = re.compile(pattern)
                curMatch = patternObj.search(self.msg)
                if bool(curMatch):
                    # If the message matches one of the patterns, 
                    # then add the requestActivity tag
                    self.tags.append(Tags.requestActivity)
                    break
                    
            
        # Check if the message asks for an opinion
        for opinion in self.opinions:
            curPat = re.compile(opinion)
            if bool(curPat.search(self.msg)):
                # If it asks for and opinion, set the opinion tag.
                self.tags.append(Tags.opinion)
                break
        
                
        # Check for a location
        for word in self.locationWords:
            # For each word in the location words list, 
            # create the regex pattern and run the search
            curPat = re.compile(self.locationReg.format(word, word))
            result = curPat.search(self.msg)
            if result:
                # If a location was parsed, add it as attribute and set the location tag.
                self.tags.append(Tags.location)
                self.location = result.groups()[0]
                break
                

class ChatUser(threading.Thread):
    """
    This class contians method used to connect, send and receive message with 
    the chat service provided by the server.py module. The class inherits from 
    the Thread class and contains an overloaded run method. Objects of this class 
    are ment to be used as thread objects. Usage:
        
        1. Instantiate the object with destination address (String, IPv4), 
           destination port (int) and username (String)
        2. Start the thread by calling the .start() method
        
        Documentatino about the threading module:
            https://docs.python.org/3/library/threading.html#module-threading
    """
    # End of message code used to identify the end of each message sent between the server and the user
    END_OF_MSG = "::EOMsg::"
    # The pattern used to identify a kick message from the host.
    kickedMessage = re.compile("^Kicked by the host for (.*)")
    # A default message displayed if an error with the connection is found
    CONNECTION_STOPPED_MSG = "The connection with the chat server has stopped."
    # Delay set for the user input interaction. All messages the user types within a 
    # given time (GENERATE_DELAY) in seconds after the first message, are acumulated.
    GENERATE_DELAY = 1 # seconds
    
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
        # The send queue for the client
        self.sendQueue = Queue()
        # The receive queue of the client
        self.recvQueue = Queue()
        # The flag used to end the connection with the server and end the client program.
        self.stopApplication = threading.Event()
        # The rest from the last receive procedure
        self.data_recv = ""
        # The rest from the last send procedure
        self.send_rest = ""
        
        
    def run(self):
        """
        This run method contains the main routine of the user chat client. It handles the 
        sending and receiving of data. It also controlls the user interaction loop, which 
        obtains input from the user rinning the program.

        Returns
        -------
        None.

        """
        # Set the client socket to be non-blocking
        self.cliSock.setblocking(0)
        
        try:
            # initiate a TCP connection with the server on given destination address and destination port
            self.cliSock.connect_ex((self.dest, self.port))
            # The connect_ex method must be used because the client socket is non blocking:
                # See this article: https://realpython.com/python-sockets/#multi-connection-client
                
        except:
            # Write to terminal if the connection could not be established
            print(f"Unable to connect to the chat server on destination {self.dest} and port {self.port}.")
            return
        
        # List contianing the socket (for read and error checking by select)
        socketList = [self.cliSock]
        
        # Add the connection message to the send queue
        self.sendInitialMessage(self.username)
        # Start the user input thread used to obtain input from the user
        userInputThread = threading.Thread(target=self.generateOutput, daemon=True)
        userInputThread.start()
        
        while not self.stopApplication.is_set():
            # While the application is not stopped
            
            # Create the list of sockets for cheking writability
            writableList = [self.cliSock] if not self.sendQueue.empty() else []
            try:
                # Run the select command to check if the socket has received any data, 
                # has encountered an error or can send to the server.
                readable, writable, error = select.select(
                    socketList, # Check the inbound buffer of the socket
                    writableList, # Check if the send buffer is not full when there are messages to be sent
                    socketList, # Check for error
                    5 # timeout in seconds
                )
                # The usage of select and handeling receive, connect and sending is based on the following sources:
                    # https://medium.com/vaidikkapoor/understanding-non-blocking-i-o-with-python-part-1-ec31a2e2db9b
                    # http://pymotw.com/2/select/ 
            except OSError:
                # If the select function fails, then end the client program.
                self.initiateClosure()
                break
            
            if readable and not self.stopApplication.is_set():
                # If there is data in the receive buffer and the stop falg is not set, 
                # fetch the data with the receivFromServer method
                self.receiveFromServer(readable[0])
                
            if writable and not self.stopApplication.is_set():
                # If there is free space in the send buffer, then send the data in the send queue
                self.sendToServer(writable[0])
                
            while not self.recvQueue.empty():
                # Print all messages that were added to the recvQueue.
                # Remove the end of messsage code
                print("\n" + self.recvQueue.get().replace(self.END_OF_MSG, ""))
                
            if error and not self.stopApplication.is_set():
                # If there is an error with the client, then initiate closure of the program
                self.initiateClosure()
            
        
        # The client socket is closed when the while loop is done
        self.cliSock.close()
        # Waiting for the thread for the user interaction to end.
        userInputThread.join(1)
        
    def sendInitialMessage(self, user):
        """
        This method creates the conneciton message which is the first message sent 
        from the client to the server. The message is then added to the send queue. 

        Parameters
        ----------
        user : String
            The username that should be sent to the server.

        Returns
        -------
        None.

        """
        self.sendQueue.put(f"{user}")
        # Print first information to the terminal
        print(f"\nYou have joined the chat with username {user}!\n\n" + 
              "Loading old messages from the thread.\n" + 
              "----------[Start old messages]----------")
        # Add delay to show the message
        time.sleep(1)
        
    def generateOutput(self):
        """
        This method contians the loop which runs the user interaction. It takes input 
        from the user and adds it as a message to the send queue. If \"\\exit\" is 
        typed by the user, then the client program is disconnecting from the server and 
        ending the program.

        Returns
        -------
        None.

        """
        # This pattern checks if the exit command was issued by the user
        exitPattern = re.compile("^\/exit")
        # The start of the message that should be sent
        usernameString = f"{self.username}: "
        while not self.stopApplication.is_set():
            # While the stop flag is not set 
            # Obtian the start timestamp
            startTime = time.time()
            # Definition of the variable containing the total message (can consist of several messages)
            totalMsg = ""
            while (time.time() - startTime) < self.GENERATE_DELAY:
                # While the time difference is less than the time specified self.Generate_Delay 
                # then add to the total message variable
                
                # Wait for input from the user
                msg = input()
                if bool(exitPattern.search(msg)):
                    # If the exit command was detected set the stop flag
                    print("You are disconnecting from the chat.")
                    self.stopApplication.set()
                    return
                else:
                    # if the cinput is normal, add it to the rest of the messages
                    print(usernameString + msg)
                    totalMsg += usernameString + msg + self.END_OF_MSG
            
            # Add the input data to the send queue
            self.sendQueue.put(totalMsg[len(usernameString):-len(self.END_OF_MSG)])
        
        
    def receiveFromServer(self, cliSock):
        """
        This method executes the receive process of the client connection.
        It fetches the first 4096 Bytes from the receive buffer and adds it to 
        the receive queue.

        Parameters
        ----------
        cliSock : Socket object
            Reference to the socket object of the client.

        Returns
        -------
        None.

        """
        # Variable containing the received data
        cur_recv = ""
        
        try:
            cur_recv = cliSock.recv(4096).decode()
        except Exception:
            # If the recv method raises an exception, 
            # then the client program is closed
            self.initiateClosure()
            return
            
        # Add the received message to the rest from the previous read cycle.
        self.data_recv += cur_recv
        
        if len(cur_recv) == 0:
            # If the socket fetched 0 bytes from the receive buffer, 
            # a disconnected connection is indicated.
            # The connection is therefore closed
            self.initiateClosure()
            return
        
        # Create a list of all received messages
        msgList = self.data_recv.split(self.END_OF_MSG)
        # Add the uncompleate message (empty string if there is no rest)
        self.data_recv = msgList.pop()
    
        for msg in msgList:
            # For each message check that it is not a connection end message
            curKickedMatch = self.kickedMessage.search(msg) 
            if bool(curKickedMatch):
                # The server has sent a kick message 
                reason = curKickedMatch.groups()[0]
                # The client socket is therefore closed with the reason 
                # given by the server.
                self.initiateClosure(reason if reason else " unknown.")
            else:
                # If it is a normal message, add it to the receive queue, 
                # ino order to print it to the user.
                self.recvQueue.put(msg)
                    
            
    def sendToServer(self, cliSock):
        """
        This method sends all the messages in the send queue of the client.

        Parameters
        ----------
        cliSock : Socket object
            Reference to the socket object of the client

        Returns
        -------
        None.

        """
        for i in range(self.sendQueue.qsize()):
            # For each message in the send queue at the moment this method is called
            
            # Variable for the total sent data for each message. 
            dataSent = 0
            # The encoded message which should be sent to the server.
            curMsg = (f"{self.username}: " + self.sendQueue.get() + self.END_OF_MSG).encode()
            while dataSent < len(curMsg):
                # Continue to send the message while the sent data is less than the length of the message.
                try:
                    # Try to send
                    cur_sent = cliSock.send(curMsg[dataSent:])
                except BlockingIOError:
                    # The send buffer is full. Save the rest of the message
                    self.sendRest = curMsg[(dataSent + cur_sent):]
                    return
                except OSError:
                    # If the recv method raises an exception other than OSError.BlockingIOError, 
                    # then the client program is closed.
                    self.initiateClosure()
                    return
                
                # Add the number of sent bytes to the total
                dataSent += cur_sent
    
    def initiateClosure(self, reason=""):
        """
        This method initiates the termination of the client socket. 
        A reason for the termination is printed to the erminal if provided 
        as argument to this method.
    
        Parameters
        ----------
        reason : String, optional
            The reason for the disconnection from the server. The default is "".
    
        Returns
        -------
        None.
    
        """
        
        if not self.stopApplication.is_set():
            # If not the method has already been called, execute the termination 
            print("\n\n" + self.CONNECTION_STOPPED_MSG)
            # Set the stop application flag
            self.stopApplication.set()
            if reason != "":
                # print the reason if it is provided.
                print("\nYou have been removed from the chat by the host. " +
                      f"The following reason was given: {reason}")
        
        
class ChatBot(ChatUser, threading.Thread):
    """
    This class represents the basic chat bot which connects to the chat server.
    It inherits from the ChatUser class and the Thread class. It can therefore 
    be used in the same way as the Chat user (see ChatUser classs for usage). 
    The overloaded methods are: 
        
        run(): The controller method of the bot thread
        
        generateResponse(): The method used for generating output from the bot.
                            Uses the MsgAnalysis class.
            
        initiateClosure(): Closes the bot without printing to the terminal
    
        sendInitialMessage(): Add a connect message to the send queue of the 
                              bot (nothing is printed to terminal).
    
        New Method introduced for bots:
            getBotResponse(): Generates special response. Each bot that inherits 
                              this class should overwrite the method in order to 
                              generate unique responses.
                              
    """
    
    # Response delay used to avoid sending all messages sent withing rappid succession
    BOT_RESPONSE_DELAY = 1
    
    def __init__(self, dest, port, username="Simple_Chat_Bot"):
        ChatUser.__init__(self, dest, port, username)
        
        # Pattern used to match messages that should not be replied to by the bot
        self.replyFilter = re.compile("^(.*[Bb]ot): " + # Do not reply to bots
                                      "|[-]+\[Start new messages\][-]+|" + # Do not reply to the separation lines
                                      "User .*[bB]ot has joined the chat!" + # Do not reply to join messages about bots
                                      "|Host: User .* left the chat\.") # Do not reply to disconnect messages from the server
        
        # Responses sent if the message asks for an opinion        
        self.opinionResponses = ["I think it is nice!", 
                                 "I am not sure, try to ask someone else.", 
                                 "I dont`t like it.", 
                                 "Let me make up my mind first!"]
        
        self.generalQuestionResponse = ["I don`t know.", 
                                        "You need to ask someone else!", 
                                        "Give me a moment to find out."]
        
        # Responses sent if the message is a statement
        self.statementResponses = ["If you say so!", 
                                   "I did not know that.", 
                                   "How can you say something like that.", 
                                   "Are you sure about that?", 
                                   "Can you prove it?"]
        
        # Responses when the message is about the weather
        self.weatherResponse = ["I do not want to talk about the weather. It is boring and always depressing!", 
                                "I have the same question.", 
                                "If you want to talk about the weather, you have to talk to someone else."]
        
        # Responses used when the message is about locations
        self.locationResponse = ["I am not an expert in geography unfortunatly, " + 
                                 "maybe some one else can help with this?"]
        
        # Messages sent if the received message is to too complicated or not classifyed by the MsgAnalysis class
        self.generalResponse = ["I am not sure if I understand your message.\n Could you please clarify?",
                           "Please write in english, so I can understand you!"]
        
        # Greetings for response to join messages
        self.greetings = ["Hi", "Hello", "A good day to you,", "How are you today"]
        
        
    def run(self):
        """
        This method contains the main routine for handeling receiving and sending 
        for the client socket.

        Returns
        -------
        None.

        """
        try:
            # Try to establish a TCP connection with the server
            self.cliSock.connect((self.dest, self.port))
        except:
            # Write to terminal if the connection could not be established
            print(f"Unable to connect to the chat server on destination {self.dest} and port {self.port}.")
            return
        
        # The connection message is sent containing the username (botname)
        self.sendInitialMessage(self.username)
        # Push the initial message to the send buffer
        self.sendToServer(self.cliSock)
        while not self.stopApplication.is_set():
            # While the application is not stopped, run the receive/send process
            if not self.stopApplication.is_set():
                # If the application is running, receive from buffer.
                
                # Delay used to prevent the bot from replying to all messages that 
                # are received in short succession
                time.sleep(self.BOT_RESPONSE_DELAY)
                # Run the receive method
                self.receiveFromServer(self.cliSock)
            
            # Respond to the received messages
            self.generateResponse()
            # Send the response to the server if there is data in the send queue.
            if not self.stopApplication.is_set() and not self.sendQueue.empty():
                self.sendToServer(self.cliSock)
            
    def initiateClosure(self, reason=""):
        """
        This method initiates the termination of the client socket for the bot.
        
        Parameters
        ----------
        reason : String
            This argument is a string containing the reason for why the server 
            stopped the connection. Because this is a bot, the reason should be "" and
            therefore ignored.
        """
        # The stopApplication flag is set in order to break the while loop in the main thread 
        self.stopApplication.set()
        
        
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
        # Current message which should be responded to
        curMsg = ""
        while self.recvQueue.qsize() > 0:
            # If the receive queue contains more than one message, 
            # then all messages are dropped except one (the latest replyable message)
            msg = self.recvQueue.get()
            
            if not bool(self.replyFilter.search(msg)):
                # The message that will be replied to by the bot is set as curent message
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
            else:
                # Return a general response to the question
                return(random.choice(self.generalQuestionResponse))
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
        # The  constructor raises an exception if the worldcities file does not exist.
        self.YrObj = yr.WeatherApi()
                
    def getBotResponse(self, msgObj):
        """
        This method generates a response to the message provided as argument.
        The response is specific for the Weatherbot. 

        Parameters
        ----------
        msgObj : MsgAnalysis
            An object with the message that should be responded to.
            The object should contian the result of classsification process
            (see docstring of MsgAnalysis). 

        Returns
        -------
        The method returns a string, which is the response to the message 
        provided as argument to this method.

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
                        try:
                            airTemp, cloudAreaFrac = self.YrObj.getCurrentWeatherData(msgObj.location)
                        except:
                            return("I am unable to reach the MET Api. Could you please make sure I have access to the Internet?")
                        
                        # Add message about the weather for the given location
                        return("The weather in " + msgObj.location + 
                                           " is " + self.YrObj.convertCloudArea(cloudAreaFrac) + 
                                           " and " + self.YrObj.convertTemperature(airTemp) + ". " + 
                                           ("I like it!" if airTemp > 15 and cloudAreaFrac < 10 else "I do not like it!") + 
                                           "\n This information is based on weather data from MET Norway and location data from simplemaps.")
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
                        try:
                            airTemp, cloudAreaFrac = self.YrObj.getCurrentWeatherData(msgObj.location)
                        except:
                            return("I am unable to reach the MET Api. Could you please make sure I have access to the Internet?")
                        
                        # Send a message informing about the temperature for the next hour.
                        return("The temperature in " + msgObj.location + 
                                           " is " + str(self.YrObj.curData['Air temperature']) 
                                           + " degree celcius!" + 
                                           "\n This information is based on weather data from MET Norway and location data from simplemaps.")
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
                        try:
                            airTemp, cloudAreaFrac = self.YrObj.getCurrentWeatherData(msgObj.location)
                        except:
                            return("I am unable to reach the MET Api. Could you please make sure I have access to the Internet?")
                        
                        # Send a message about the weather at the given location the next hour.
                        return("The temperature in " + msgObj.location + 
                                          " is " + str(self.YrObj.curData['Air temperature']) +
                                          " degree celcius! The sky is " + 
                                          str(self.YrObj.convertCloudArea(self.YrObj.curData['Cloud_area_fraction'])) + 
                                          ".\n This information is based on weather data from MET Norway and location data from simplemaps.")
                                           
                    except ValueError:
                        #print("Location was not found in list") # Used for debug
                        # The location was not identified as a city.
                        return(random.choice(self.unknownLocation))
            else: 
                # Return a general response to the question
                return(random.choice(self.generalQuestionResponse))
            
        elif Tags.statement in msgObj.tags:
            #print("identified as statement/suggestion")
            return(random.choice(self.statementResponses))
        else:
            # If the message is not a statement or a question, reply with general response
            return(random.choice(self.generalResponse))
                 
class SportBot(ChatBot):
    """
    This class contians the methods used to create the response of the Sportbot. 
    It inherits from the ChatBot class. The bot can be used by first 
    instantiating an object of the class. The destination address and port should 
    be given as argumen to the constructor. The object will be a threading object 
    and the thread can be started with the method start(). The method initiateClosure 
    can be called to stop the bot.
    """
    def __init__(self, dest, port, username="Sport_Bot"):
        ChatBot.__init__(self, dest, port, username)
        
        # The unique response to some activities
        self.activityReplies = {"tennis" : ["Yes, I love tennis!", "I would like to play tennis."], 
                           "football" : ["I like football, but I prefere tennis", "I like sport in general," + 
                                         " but hearing about football now is not cheering me up right now"], 
                           "drawing" : ["I am a big sports fan, but art is not my cup of tea!", "Please, talk about something else! Maybey we can watch sport?"]}
        
        # Opinions used to respond to requests for an opinion about an activity
        self.opinionOnActivities = {Tags.sport : ["I love all kind of sport, and I am realy paying a lot of attention to {} at the moment.",  
                                             "I think that {} is one of the best sports there is!", 
                                             "I could watch {} all day!", "I could play {} all day."], 
                               Tags.art : ["I am not very interested in art. Sorry. But we could talk about sports!", "I dont like art.", 
                                           "I prefere the art of creating the perfect stop-ball in tennis."]} 
        # Response to weather messages 
        self.weatherOpinion = ["I do not care about the weather.", "A true athlete works in any weather!", "The weather is always nice enough in my opinion", 
                        "There is nothing called bad weather!"]
        
    def getBotResponse(self, msgObj):
        """
        This method generates a response to the message provided as argument.
        The response is specific for the Sportbot. 

        Parameters
        ----------
        msgObj : MsgAnalysis
            An object with the message that should be responded to.
            The object should contian the result of classsification process
            (see docstring of MsgAnalysis). 

        Returns
        -------
        The method returns a string, which is the response to the message 
        provided as argument to this method.
        """
        if Tags.question in msgObj.tags:
            # Is the message a question?
            if Tags.opinion in msgObj.tags:
                # Is the message a request for an opinion on a subject?
                if Tags.activity in msgObj.tags:
                    # Is the message asking for an opinion on an activity?
                    if Tags.sport in msgObj.tags:
                        # Is the message about sport?
                       return(     # Put a random message into the send queue
                            random.choice(self.opinionOnActivities[Tags.sport]).format(msgObj.activity)
                            )
                    else:
                        # The message is about art.
                        return(
                                random.choice(self.opinionOnActivities[Tags.art])
                            )
                elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                    # If the message asks for an opinion about the weather
                    return(random.choice(self.weatherOpinion))
                else:
                    # General response to opinion messages
                    return(random.choice(self.opinionResponses))
                    
            elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                # The message asks about the weather
                return(random.choice(self.weatherOpinion))
                
            elif Tags.activity in msgObj.tags:
                if msgObj.activity in ["draw", "paint", "painting"]:
                    msgObj.activity = "drawing"
                return(random.choice(self.activityReplies[msgObj.activity]))
                
            else: 
                # Return a general response to the question
                return(random.choice(self.generalQuestionResponse))
            
        elif Tags.statement in msgObj.tags:
            # Is the message a statement or a request for an activity?
            if Tags.requestActivity in msgObj.tags:
                # The message is a request about an acitivty:
                if msgObj.activity in ["draw", "paint", "painting"]:
                    msgObj.activity = "drawing"
                return(random.choice(self.activityReplies[msgObj.activity]))
            else:
                # return default statement response.
                return(random.choice(self.statementResponses))
        else:
            # General response
            return(random.choice(self.generalResponse))
        
class ArtBot(ChatBot):
    """
    This class contians the methods used to create the response of the Artbot. 
    It inherits from the ChatBot class. The bot can be used by first 
    instantiating an object of the class. The destination address and port should 
    be given as argumen to the constructor. The object will be a threading object 
    and the thread can be started with the method start(). The method initiateClosure 
    can be called to stop the bot.
    """
    
    def __init__(self, dest, port, username="Art_Bot"):
        ChatBot.__init__(self, dest, port, username)
        
        # Unique responses to activities for the Artbo
        self.activityReplies = {"tennis" : ["Tennis! Sounds interesting. What is it?", "I would like to trie, but you would have to teach me!", "No, I am not interested"], 
                           "football" : ["No football for me, please!", "I don`t like football. Can we talk about something else?", "Football. Such a pointless activity!"], 
                           "drawing" : ["Yes, I will never say no to that.", "That is a good idea.", "Perfect, I have practiced my drawing capabilities lately."]}
        
        # Responses for requests about opinions on an activity
        self.opinionOnActivities = {"football" : ["I do not like football. I think that it is compleatly mental to kick around a ball all day, while you can spend your time crating real art.", 
                                                  "I do not have much symphaty with that sport.", "Lets talk about something relevant!"], 
                                    "tennis" : ["I am not sure yet. I need to try it first.", "It looks like a cool activity. I would like to try it once."], 
                               "drawing" : ["I love to create art with the pencile.", "It is my faivorit activity.", 
                                           "With all my hart, i like to paint and draw!"]} 
        
        # Response to weather messages.
        self.weatherOpinion = ["I like all kinds of weather. Any weather can provide an interesting motive for a drawing.", 
                               "Let the weather be what it is and live with it!", "I can`t complain. It is nice enough for me!"]
        
    def getBotResponse(self, msgObj):
        """
        This method generates a response to the message provided as argument.
        The response is specific for the Artbot. 

        Parameters
        ----------
        msgObj : MsgAnalysis
            An object with the message that should be responded to.
            The object should contian the result of classsification process
            (see docstring of MsgAnalysis). 

        Returns
        -------
        The method returns a string, which is the response to the message 
        provided as argument to this method.

        """
        if Tags.question in msgObj.tags:
            # Is the message a question?
            if Tags.opinion in msgObj.tags:
                # Is the message a request for an opinion on a subject?
                if Tags.activity in msgObj.tags:
                    # Is the message asking for an opinion on an activity?
                    if msgObj.activity in ["draw", "paint", "painting"]:
                        msgObj.activity = "drawing"
                    return(random.choice(self.opinionOnActivities[msgObj.activity]))
                    
                elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                    # If the message asks for an opinion about the weather
                    return(random.choice(self.weatherOpinion))
                else:
                    # General response to opinion messages
                    return(random.choice(self.opinionResponses))
                    
            elif Tags.temperature in msgObj.tags or Tags.weather in msgObj.tags:
                # The message asks about the weather
                return(random.choice(self.weatherOpinion))
                
            elif Tags.activity in msgObj.tags:
                if msgObj.activity in ["draw", "paint", "painting"]:
                    msgObj.activity = "drawing"
                return(random.choice(self.activityReplies[msgObj.activity]))
                
            else: 
                # Return a general response to the question
                return(random.choice(self.generalQuestionResponse))
            
        elif Tags.statement in msgObj.tags:
            # Is the message a statement or a request for an activity?
            if Tags.requestActivity in msgObj.tags:
                # The message is a request about an acitivty:
                if msgObj.activity in ["draw", "paint", "painting"]:
                    msgObj.activity = "drawing"
                return(random.choice(self.activityReplies[msgObj.activity]))
            else:
                # return default statement response.
                return(random.choice(self.statementResponses))
        else:
            # General response
            return(random.choice(self.generalResponse))
            
            
if __name__ == "__main__":
    # Instantiate an argument parser to handle the commandline arguments and creating a help message.
    parser = argparse.ArgumentParser(description="This program starts all chatbots defined, " + 
                                     "including a user client, and connects them to the server.")
    # Adding a commandline parameter -d for the destination address. The user can provide an address to the 
    # chat server as a string.
    parser.add_argument("-d", "--Dest", nargs='?', default=socket.gethostbyname(socket.gethostname())
                        , metavar="DESTINATION", type=str, help="The IPv4 address of the server. String. Default: localhost")
    # Adding a commandline parameter for the destination port. 
    parser.add_argument("-p", "--Port", nargs='?', default=2020, metavar="PORT", type=int, 
                        help="Portnumber that the server is listening on. Must be an Integer. Default: 2020")
    # Adding a commandline paramter to add a curstom username to the user client. The default value is "Chat_User"
    parser.add_argument("-u", "--Username", nargs='?', default="Chat_User", metavar="USERNAME", type=str, 
                        help="Username displayed with messages sent from the client. String. Default: Chat_user")
    
    argParsed = parser.parse_args()
    # Create a thread for the client user connection
    testChat = ChatUser(argParsed.Dest, argParsed.Port, argParsed.Username)
    testChat.start()
    
    time.sleep(1)
    # Start a simple chat bot.
    testBot = ChatBot(argParsed.Dest, argParsed.Port)
    testBot.start()
    
    time.sleep(1)
    try:
        # try to import the YrInterface module.
        import YrInterface as yr
        
        # Start the weatherBot. 
        weatherBot = WeatherBot(argParsed.Dest, argParsed.Port)
        weatherBot.start()
    except:
        # If the weather bot fails, then start a simple bot instead
        weatherBot = ChatBot(argParsed.Dest, argParsed.Port, "Weather_substitute")
        weatherBot.start()
    
    time.sleep(1)
    # Start the SportBot
    sportBot = SportBot(argParsed.Dest, argParsed.Port)
    sportBot.start()
    
    time.sleep(1)
    # Start the ArtBot
    artBot = ArtBot(argParsed.Dest, argParsed.Port)
    artBot.start()
    
    testChat.join()
    # Stop all bots if the client thread is finished
    if testBot.is_alive():
        testBot.initiateClosure()
    testBot.join()
    
    if weatherBot.is_alive():
        weatherBot.initiateClosure()
    weatherBot.join()
    
    if sportBot.is_alive():
        sportBot.initiateClosure()
    sportBot.join()
    
    if artBot.is_alive():
        artBot.initiateClosure()
    artBot.join()
    