# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 00:50:00 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

This code has been writen for python 3.

This module is part of the solution to the individual 
portfolio assignemnt in the course DATA2410 - Datanettverk 
og skytjenester. The module contains the classes used to 
host the single threaded chat service. This includes handeling 
TCP connections from users, receiving messages from users and 
forwarding them to all other users. It also includes generating 
messages that initiate conversations.

Three classes:
    HostBot class: This class simulates the host user which contians 
    the list of all possible messages that can be sent to the users. It 
    also contains a method to pick a message from the list. Each 
    SimpleChatServer object does have one HostBot object.
    
    ChatSocket class: An object of this class represents a client which 
    is connected to the server. Each SimpleChatServer instance can have 
    several ChatSocket objects associated.
    
    SimpleChatServer class: This is the controller class of the server 
    side. It contains methods used to listen to incomming connections 
    from clients, receive messages and forward them to clients. There 
    is also implemented a small controll pannel, which can be used to 
    manage the chat thread as an administrator.
    
If this file is executed, it instantiates the SimpleChatServer class 
to create an object which host the chat service. You can specify the port 
that the server should listen on as an argument. The following line starts 
a server which is listening on port 2020:

python3 server.py --Port 2020

on Windows: python server.py --Port 2020

You can see the help text by adding the --help option:
    
    Python3 server.py --help
    
The argument \"Port\" is optional. The server has default port 2020. The address 
which the server answers on is any address associated with the network interfaces 
of the end point this program is running on. 


"""
# Importing the socket module 
import socket
import select
# Importing the module used for logging data to a log file
import logging
# Importing a module used to implement and run threads
import threading
# Importing a module which parses arguments and adds help information
import argparse
# Importing the regex library
import re
# Importing a Queue datastructure
from queue import Queue 
# Importing the random module used to pick a random message for the host bot
import random

# Modules for working with time and dates
import time
from datetime import datetime
# Module used to create directorys which are missing in the application file structure
import os

class ChatSocket:
    """
    Objects of this class represents the clients which are connected to the chat service.
    The SimpleChatServer is dependant on this class.
    """
    
    def __init__(self, socketObj, history):
        # Attribute containing the rest from the last receive procedure
        self.recvRest = ""
        # The username of the user 
        self.username = ""
        # The send queue containing messages that should be sent to the user.
        self.sendQueue = Queue()
        # The reason why the user is getting removed
        self.kickReason = ""
        # A reference to the client socket object is stored
        self.clientSocket = socketObj
        
        for i in range(len(history)):
            # The existing thread messages are added to the send queue.
            # This way, the client will receive all the messages that were sent 
            # in the chat before the client joined the chat.
            self.sendQueue.put(history[i])
            
        # Add the start new messages indication to indicate that the 
        # next messages are sent after the user connected to the server.
        self.sendQueue.put("------------[Start new messages]------------")
        # Get the port and destination address of the client
        self.destAddress = socketObj.getpeername()
        # The time stamp of the last received message
        self.lastRecvTime = datetime.now()
        # Number of received messages. Used to detect a user which sends too 
        # many messages (spaming). 
        self.recvCounter = 0
        # This Flag is set if the server encounters problems with receiving 
        # or sending to the client.
        self.isBroken = False
        
        
class HostBot:
    """
    This class represents the host which is initiating conversations 
    in the chat thread. The method hostThread in the SimpleChatServer
    class creates an instance of this class to send messages to all 
    connected clients.
    
    The messages which are sent from the host are saved in the 
    conversationInitiators.txt in the same forlder as the server.py 
    file. If the file is not found, some default messages defined in 
    the code are used.
    
    Usage:
        Instantiate an object of this class and then call getCurMsg 
        to get the message set as current message (self.curMsg). If the 
        message lifetime has exeeded the limit (MESSAGE_LIFETIME), then 
        a new message is set as current message and returned. The user 
        can update the current message independent of the time by calling 
        the setCurMsg (returns the new message).
        
    """
    # The contstant defining the period a message should be active (seconds)
    MESSAGE_LIFETIME = 10
    def __init__(self):
        try:
            # The messages that could be sent by the host, are read from file 
            with open(".\\conversationInitiators.txt", "r") as file:
                self.conversationInitiators = file.read().split("\n")
            
            # Empty lines are removed
            while self.conversationInitiators[-1] == '':
                # While there is an empty string at the end of the list
                # -> remove the empty string
                self.conversationInitiators.pop()
            
            if len(self.conversationInitiators) == 0:
                # Raise RuntimeError if the file is empty
                raise RuntimeError
        except (FileNotFoundError, RuntimeError):
            # If the file was not found or has no content
            # -> write error to the log and add a default message to conversationInitiators
            logging.error("The file, conversationInitiators.txt, was not found!")
            self.conversationInitiators = ["What is the temperature in Oslo?", 
                                           "Is it sunny in Oslo?", 
                                           "How is the weather in Berlin?", 
                                           "It is cloudy in Oslo!", 
                                           "It is a bad day!", 
                                           "Do you like the weather in London?", 
                                           "How would you rate the weather in Paris?", 
                                           "We could play some football?", 
                                           "Can we paint a painting?", 
                                           "What do you think about watching tennis?", 
                                           "Do you like to play tennis?"]
        
        # The attribute containing the current message
        self.curMsg = "What is the temperature in Oslo?"
        # A message is set as the current message to be sent
        self.setCurMsg()
        
    
    def getCurMsg(self):
        """
        This method returns the message that should be sent from the host 
        at the given time. A new message is set if the MESSAGE_LIFETIME 
        has been reached for the current message. 

        Returns
        -------
        String
            The current message the host should send.

        """
        if time.time()-self.msgStartTime > self.MESSAGE_LIFETIME:
            # If the current message has been active for longer than the 
            # value given by MESSAGE_LIFETIME, then a new message is set.
            # The current message is then returned.
            return(self.setCurMsg())
        
        else:
            return(self.curMsg)
    
    def setCurMsg(self):
        """
        This method sets the current message and stores the start timestamp of 
        the message.

        Returns
        -------
        self.curMsg - String
            The new message is returned.

        """
        # A new message is set
        self.curMsg = random.choice(self.conversationInitiators)
        # The start time of the message is captured
        self.msgStartTime = time.time()
        # Return the new message
        return(self.curMsg)

class SimpleChatServer:
    """
    The SimpleChatServer class has the task to host and controll one single chat thread.
    
    
    """

    # End of message code used to identify the end of each message sent between the server and the user
    END_OF_MSG = "::EOMsg::"
    # The maximal number of bytes received per receive sycle 
    MAX_RCV = 4096*5
    # Regex pattern used to find the username
    botnamePattern = re.compile("^(.*): ")
    # The username of the host
    HOSTBOT_UNAME = "Host"
    # The time between host messages (seconds)
    HOST_PERIOD = 30
    # The main part of the kick message
    KICK_MSG = "Kicked by the host for "
    # The regex pattern used to parse the commands issued by the administrator
    cmdPattern = re.compile("^([^ ]*) {0,1}(.*)$")
    
    # Constants used in checking for spam by users.
    # The server kicks a user if the user sends SPAM_MSG_NUMBER messages 
    # within SPAM_SECONDS.
    SPAM_MSG_NUMBER = 10
    SPAM_SECONDS = 4
    
    def __init__(self, port):
        # Verify that the port provided as argument to the constructor is valid
        if type(port)!=int or port < 0 or port > 65535:
            raise ValueError(f"The provided port {port} is not valid. \
                             Please provide a decimal number between 0 and 65535")
        
        # The port is added to the port attribute
        self.port = port
        # The isRunning flag is set to False (This attribute indicates if the server is running)
        self.isRunning = False
        
        # Flags used to signal accross threads. This flags are thread-safe:
            # https://docs.python.org/3/library/threading.html#threading.Event
        self.stopApplication = threading.Event()
        self.stopUserInteraction = threading.Event()
        
        # The list of all connected users. 
        # It should contain instances of the ChatSocket classs
        self.chatUsers = []
        # A list containing all messages which were sent since the service started
        self.history = []
        
        # List of sockets that should be checked by the select command 
        self.checkReadable = [] # Select checks if the sockets in this list are readable (does the buffer contain data?)
        self.checkWritable = [] # Select checks if the socket connections in this list can be used to send.
        self.checkError = [] # Select checks if the socket connections in the list have errors.
        
        # A list containing references to client sockets which should be closed in the next iteration.
        self.closeNext = []
        # A list containing all sockets that should send a close message to the client and then be removed
        self.finishRemovalList = []
        
        # This queue contains the references to each send and receive thread created in the mainThread method
        self.activeThreads = Queue()
        # Defining the commands which can be used to controll the service
        # Each key in the dictionary, command name, have a list with a general description of the command, 
        # Description of the arguments and a reference to the function this command should execute.
        self.cmdSet = {"listConnections" : ["Prints a list of all connected users. ", 
                                         "The command takes no arguments.", self.listConnections], 
                       "kick": ["Disconnects a specified user from the server. ", 
                                "The command takes two arguments: username of the user (mandatory) " +
                                "and the reason for the kick (optional). The reason can be given " +
                                "as a space separated words. Eks: kick User Due to service overload.", self.kickUser],
                       "exit" : ["Stops the chat service. ", "The command takes no arguments.", self.stopService]}
        
        
    def startService(self):
        """
        This method is called to start the chat service. It creates the main thread which listenas for 
        client connecitons, receives data and sends data. It also contians the user interaction loop used 
        to get commands defined in the self.cmdSet dictionary.

        Returns
        -------
        None.

        """
        # Defines the main server socket with the IPv4 address family (AF_INET) 
        # and the TCP protocol (SOCK_STREAM) as domain and type
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Binds the server socket to the given port and any address associated to any network card ont he ensystem 
        # running this program.
        self.serverSocket.bind(('', self.port))
        # The server starts listening on the given port. 
        # The number of unaccepted connections to the server before the server refuses any new connections, is 5.
        self.serverSocket.listen(5)
        # The server socket is added to the check readable list so select can check if there ar new connections 
        # Which the server socket can accept.
        self.checkReadable.insert(0, self.serverSocket) 
        
        logging.info("Service is listening to incomming connections on port %s.", str(self.port))
        # Print start information about the program and the server
        print("Python Chat service\tCreated by Bernt Olsen, student at OsloMet.\n")
        print("Service is listening to incomming connections on port {}. \n".format(str(self.port)))
        # Indicate that the server is running
        self.isRunning = True
        # Create and start the main thread
        mainThread = threading.Thread(target=self.mainThread)
        mainThread.start()
        
        # List all commands with their descriptions
        print(self.listCommands())
        
        # User interaciton loop
        while not self.stopUserInteraction.is_set():
            # Continue until the stopUserInteraction flag is set.
            # Await input
            cmd = input("Host $> ")
            # Extract the command and arguments
            matchResult = self.cmdPattern.search(cmd)
            
            if bool(matchResult):
                # If a command was parsed, then get the command and attributes
                cmd = matchResult.groups()[0] # command
                arguments = matchResult.groups()[1].split(" ") # arguments
                if cmd in self.cmdSet:
                    # If the command is recognized
                    if cmd == "kick":
                        reason = ""
                        # Check the arguments if the kick command is given
                        if len(arguments) == 0 or arguments[0] == '':
                            print("No username was specified. Please specify the username \
                                  of the user that should be removed.")
                        else:
                            username = arguments[0]
                            if len(arguments) > 1:
                                reason = arguments[1]
                                for word in arguments[2:]:
                                    reason += " " + word
                        
                            # Run the kick method     
                            if not self.cmdSet[cmd][2](username, reason):
                                print(f"User with username {username} was not found!")
                            else:
                                print(f"User {username} was removed!")
                    elif cmd == "exit":
                        self.cmdSet[cmd][2]("The service is stopping!")
                    else:
                        # Execute method associated with the command
                        self.cmdSet[cmd][2]()
                else: 
                   print(f"The command {cmd} was not recognized!")
            else: 
               print(f"The command {cmd} was not recognized!")
        
        print("    Waiting for threads to finish.", end="\r")
        while mainThread.is_alive():
            self.waitIndication()
            
        mainThread.join()
        print("[OK] Waiting for threads to finish.")
        self.serverSocket.close()
        self.isRunning = False
        print("Service stopped successfully!\n")
        logging.info("Service stoped successfully!")
        
    def mainThread(self):
        
        hostbotThread = threading.Thread(target=self.hostbotThread, daemon=True)
        hostbotThread.start()

        while not self.stopApplication.is_set() and (len(self.checkWritable) > 0 or len(self.checkReadable) > 0):
            try:
                readable, writable, err = select.select(self.checkReadable, self.checkWritable, self.checkError, 10)
            except OSError as E:
                logging.error(f"The select function raised the following exception: {E}")
                readable, writable, err = []
                # Stoping program
                print(f"Fatal error in main thread. Program is closing: {E}")
                self.stopApplication.set()
                self.stopUserInteraction.set()
                
                
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
            
            while len(self.finishRemovalList) != 0:
                self.finishRemoval(self.finishRemovalList.pop())
            
            while len(err) != 0:
                logging.info("Closing socket due to an error detected by the select function.")
                curSocket = err.pop()
                if not curSocket._closed:
                    self.removeClient(curSocket)
                    
                
            while len(self.closeNext) != 0:
                curSocket = self.closeNext.pop()
                if not curSocket._closed:
                    # If the socket has not already been closed, close it. 
                    self.removeClient(curSocket)
        
        hostbotThread.join(1)
            
    def hostbotThread(self):
        """
        This method is the target of the hostThread object from the main thread 
        and contains the routin which is run by the hostThread. The routine 
        instantiates a HostBot object, gets the message set by the HostBot 
        and sends puts it in each send queue. This is repeated in a cycle with 
        the length given by the HOST_PERIOD constant. The thread ends when the 
        stopApplication flag is set.
        
        Returns
        -------
        None.

        """
        # An HostBot object is instantiated
        self.hostbot = HostBot()
        
        while not self.stopApplication.is_set():
            # While the stopApplication flag is not set
            logging.info("A new message is sent from host")
            # Get the current message set by the HostBot object
            msg = f"\n{self.HOSTBOT_UNAME}: {self.hostbot.getCurMsg()}"
            # Add the message to the thread cache
            self.history.append(msg)

            for user in self.chatUsers:
                # Add the message to each send queue
                user.sendQueue.put(msg)
            # Put the thread in idle for the given amount of seconds (HOST_PERIOD)
            time.sleep(self.HOST_PERIOD)
            
    def acceptConnection(self):
        client, src = self.serverSocket.accept()
        logging.info(f"New client connection accepted for source {src}.")

        curChatSocket = ChatSocket(client, self.history)
        self.chatUsers.append(curChatSocket)
        
        self.checkReadable.append(client)
        self.checkWritable.append(client)
        self.checkError.append(client)
    
    def sendToClient(self, cliSock):
        curChatUser = self.searchChatUser(cliSock)
        
        for i in range(curChatUser.sendQueue.qsize()):
            sendMsg = curChatUser.sendQueue.get()
            #logging.info(f"Sending \"{sendMsg}\" to {curChatUser.username} {curChatUser.destAddress}")
            msg = (sendMsg + self.END_OF_MSG).encode()
            msgLen = len(msg)
            sentBytes = 0
            while sentBytes < msgLen:    
                try:
                    curSent = cliSock.send(msg[sentBytes:])
                except (ConnectionAbortedError, ConnectionResetError) as E:
                    self.connectionErrorHandling(curChatUser, cliSock, str(E))
                    return
                
                sentBytes += curSent
                if curSent == 0:
                    self.connectionErrorHandling(curChatUser, cliSock)
                    
    def connectionErrorHandling(self, curChatUser, cliSock, E=""):
        if not curChatUser.isBroken:
            logging.warning(f"The connection with the client {curChatUser.username} {curChatUser.destAddress} has ended. {E}")
            # Set the isBroken flag to indicate that the client cannot receive.
            curChatUser.isBroken = True
            self.closeNext.append(cliSock)
            
    def recvFromClient(self, cliSock):
        """
        This method reads the content of the receive buffer of the given client socket.
        A reference to the client socket must be provided as argument to this method.

        Parameters
        ----------
        cliSock : Socket
            Client socket which has a non empty receive buffer.

        Returns
        -------
        None.

        """
        curChatUser = self.searchChatUser(cliSock)
        
        logging.info(f"Receiving from client {curChatUser.destAddress}")
        # Compiling a pattern for matching end of message
        pattern = re.compile(self.END_OF_MSG)
        # # Gets an address to the list of important variables for the given socket 
        # clientVariables = self.sendQueues[cliSock.getpeername()]
        # Extracts the rest of the previous reception. This variable contains 
        # a non empty string whenever the previous reception received a portion of the next message 
        # in the same process.
        data_recv = curChatUser.recvRest
        # Definition of a variable for the new data
        cur_recv = ""
        
        while not bool(pattern.search(data_recv)) and len(data_recv) < self.MAX_RCV: 
            # While the received data does not contain the end of message code
            # or the received data does not exceed the maximal size, continue 
            # reading from buffer.
            try:
                # Read from the buffer of the client socket
                cur_recv = cliSock.recv(4096).decode()
            except (ConnectionAbortedError, ConnectionResetError) as E:
                self.connectionErrorHandling(curChatUser, cliSock, str(E))
                return
                
            if len(cur_recv) == 0:
                # If the recv method returned nothing, then the connection is closed.
                # The data that was sent before an EOMsg was found will be dropped
                self.connectionErrorHandling(curChatUser, cliSock)
                return
            
            # The received data is added to the data from the previous receive cycle
            data_recv = data_recv + cur_recv
        
        logging.info(f"Data received: {data_recv}")
        
        # Cleaning up the received data and create a list of all messages 
        # contained in the received message 
        msgList = data_recv.replace("\n", "").split(self.END_OF_MSG)
        #logging.info(f"The msgList for {curChatUser.username}:" + str(msgList))
        
        # Determine if the use is spaming (10 messages within a second)
        if (datetime.now() - curChatUser.lastRecvTime).seconds <= self.SPAM_SECONDS:
            curChatUser.recvCounter += len(msgList)
            logging.info(f"Number of receptions for {curChatUser.username}: {str(curChatUser.recvCounter)}")
            if curChatUser.recvCounter >= self.SPAM_MSG_NUMBER:
                # User is spaming SPAM_MSG_NUMBER messages in SPAM_SECONDS seconds
                # The user will as a result be removed
                logging.warning(f"User {curChatUser.username} sent {self.SPAM_MSG_NUMBER} messages within {self.SPAM_SECONDS} seconds. " + 
                                "The user will be kicked for this! Type 1")
                # A reason for the removal is provided
                curChatUser.kickReason = "sending too many messages at the same time"
                # The removal is initiated
                self.closeNext.append(curChatUser.clientSocket)
                return
        elif len(msgList) > self.SPAM_MSG_NUMBER:
            # The user has sent too many messages (more than SPAM_MSG_NUMBER)
            # The user is removed
            logging.warning(f"User {curChatUser.username} sent {self.SPAM_MSG_NUMBER} in rappid succession." + 
                            "The user will be kicked for this! Type 2")
            # A reason for the removal is provided
            curChatUser.kickReason = "Sending too many messages in rapid succession!"
            # The removal is initiated
            self.closeNext.append(curChatUser.clientSocket)
            return
        else:        
            logging.info(f"Reseting receive counter {curChatUser.username}.")
            # Adding a new timestamp for the last receive time attribute:
            curChatUser.lastRecvTime = datetime.now()
            # Reset counter
            curChatUser.recvCounter = 0
            
        # The last message in the msgList is stored (emplty string, if the last messsage is complete)
        curChatUser.recvRest = msgList.pop()
        
        if curChatUser.username == "":
            # If there is no username registered for the socket, then 
            # the message must be the first message (connection message), 
            # containing only the username
            curChatUser.username = msgList[0][msgList[0].find(":") + 2 : ]
            # Send a join message to all clients
            self.populateSendQueues(f"User {curChatUser.username} has joined the chat!", cliSock)
        else:
            # The message is processed as a chat message if the username is set
            for msg in msgList:
                # All messages are forwarded to the other sockets
                self.populateSendQueues(msg, cliSock)
    
    def populateSendQueues(self, msg, cliSock):
        """
        This method is adding a message to the send queues of each client socket, 
        except the socket given as argument to this method (cliSock). The message 
        is also provided as argument (msg).
        """
        # Add the message to the chat history
        self.history.append(msg)
        for user in self.chatUsers:
            # For each client socket check that the socket is not the socket 
            # provided as argument to this method.
            if user.clientSocket != cliSock:     
                # Add the message in the send queue
                user.sendQueue.put(msg)
                
    def removeClient(self, cliSock):
        curChatUser = self.searchChatUser(cliSock)
        logging.info(f"The connection to {curChatUser.username} {curChatUser.destAddress} is closing.")
        # Send a message to all other users informing that the user is no longer active
        self.populateSendQueues(f"{self.HOSTBOT_UNAME}: User {curChatUser.username} left the chat.", cliSock)
        # Remove socket from the list of readable sockets to avoid receiving from the client
        self.checkReadable.remove(cliSock)
        # The socket is also removed from the list for error checking
        self.checkError.remove(cliSock)
        
        if not curChatUser.isBroken:
            # Add the disconnect message to the clients sendQueue
            disconnectMessage = self.KICK_MSG + curChatUser.kickReason
            curChatUser.sendQueue.put(disconnectMessage)
            # Add the socket to the list of sockets which are in the removal process
            self.finishRemovalList.append(cliSock) 
        else:
            # The connection is broken
            # Finish the removal
            self.checkWritable.remove(cliSock)
            self.chatUsers.remove(curChatUser)
            cliSock.close()
    
    def finishRemoval(self, cliSock):
        """
        This method finishies the removal of a socket. 
        It is required that the removeClient method has been 
        called for the same socket first.
        """
        # Remove the ChatSocket objecct from chatUser list
        self.chatUsers.remove(self.searchChatUser(cliSock))
        cliSock.close()
        self.checkWritable.remove(cliSock)
        
    def listConnections(self):
        """
        This method creates a list of all the connected users 
        and prints the list to the terminal
        """
        
        outString = "{:>15}{:>20}{:>30}\n".format("Username", "IPv4 Address/Port", "Time last received")
        outString += "{:>15}{:>20}{:>30}\n".format("--------", "--------", "--------")
        for connection in self.chatUsers:
            portAndAddress = str(connection.destAddress[0]) + ":" + str(connection.destAddress[1])
            username = connection.username
            lastReceived = str(connection.lastRecvTime)
            outString += f"{username:>15}{portAndAddress:>20}{lastReceived:>30}\n"
        
        print(outString)
        
    def kickUser(self, username, reason=""):
        """
        This method is used to manualy disconnect a user from the server.

        Parameters
        ----------
        username : TYPE
            The username of the user which is beeing disconnected.
            
        reason : String
            The reason why the user is disconnected by the host.
            
        Return
        ------
        Boolean
            The method returns True if the username was found and is beeing removed.
            It also returns False if the username was not found.
        """
        for user in self.chatUsers:
            # For each list in the connection dictionary
            if user.username == username:
                # If the username was found then add the reason and add the 
                # socket to the closeNext list to initiate the remove procedure
                user.kickReason = reason
                self.closeNext.append(user.clientSocket)
                # Return true to confirm that the client is removed
                logging.info(f"User {username} is removed by admin with the following reason: {user.kickReason}")
                return True
        # If the user was not recognised, then return false
        return False
    
    def listCommands(self):
        """
        This method returns a string contianing a list of all 
        commands that can be used to controll the service.

        Returns
        -------
        String
            A string containing all commands that can be used 
            to controll the service.
        """
        linePattern = re.compile("[\n]{0,1}(.{0,30}[^a-zA-Z0-9])(.*)")
        emptyString = ""
        outMsg = "Command set for the Python Chat service:\n\n"
        outMsg += "{:>20}: \n".format("Commands")
        outMsg += "{:>20}\n".format("----------")
        
        for cmd in self.cmdSet.keys():
            cmdDescription = ("Description: " + str(self.cmdSet[cmd][0]) + str(self.cmdSet[cmd][1]))
            
            matches = linePattern.search(cmdDescription)
            firstLine = matches.groups()[0]
            outMsg += f"\n{cmd:>20} - {firstLine:35}\n"
            while len(matches.groups()[1]) > 0:
                cmdDescription = matches.groups()[1]
                matches = linePattern.search(cmdDescription)
                if bool(matches):
                    outMsg += f"{emptyString:>20}   {matches.groups()[0]:35}\n"
                else:
                    outMsg += f"{emptyString:>20}   {cmdDescription:35} \n"
                    break
                    
        return(outMsg)
    
    def stopService(self, reason=""):
        """
        This method removes all connections and stops the chat service
        """
        print("Service is shutting down.")
        print("    Removing active connections.", end="\r")
        logging.info("The service is stoping due to an \"exit\" command issued by admin.")
        # End the user interaction loop.
        self.stopUserInteraction.set()
        # Remove the server socket from the check receivable list to avoid new connections
        self.checkReadable.pop(0)
        # Add all sockets to the close next list
        for curChatUser in self.chatUsers:
            curChatUser.kickReason = reason
            self.closeNext.append(curChatUser.clientSocket)
                    
        while len(self.chatUsers) > 0:
            # Wait until all connections are removed
            self.waitIndication()
            #logging.info(f"chatUser: {self.chatUsers}")
            
        print("[OK] Removing active connections.")
        logging.info("Stop procedure status: All connections are removed!")
        # Set the stopApplication flag in order to stop the program
        self.stopApplication.set()
    
    def waitIndication(self):
        print("[-]", "\r", end="")
        time.sleep(0.1)
        print("[\\]", "\r", end="")
        time.sleep(0.1)
        print("[|]", "\r", end="")
        time.sleep(0.1)
        print("[/]", "\r", end="")
        time.sleep(0.1)
            
    def searchChatUser(self, cliSock):
        """
        This method return the chatUser object corresponding to the socket 
        object given as argument to this method

        Parameters
        ----------
        cliSock : Socket object
            The socket object of the user that should be found in the chatUser list

        Returns
        -------
        ChatSocket object corresponding to the given client socket

        """
        for user in self.chatUsers:
            if user.clientSocket == cliSock:
                # Return the ChatSocket object that corresponds to the cliSock object
                return(user)
            
        # The user was not found
        raise Exception("The user was not found in the chatUser list.")

if __name__=="__main__":
    
    #Handle command line argument
    parser = argparse.ArgumentParser(description="This program starts a sigle threaded chat service.")
    parser.add_argument('-p', '--Port', nargs='?', default=2020, metavar="PORT",
                        type=int, help="The port number associated with the service")
    args = parser.parse_args()
    
    # Check that a log folder is present in the application directory
    if not os.path.isdir("./Logs"):
        # Create the folder if it does not exist
        os.mkdir("Logs")
    
    logDay = f"{datetime.now().date().__str__()}"
    logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s', 
                        filename=f"./Logs/chatServer_{logDay}.log", level=logging.INFO)
    
    server = SimpleChatServer(args.Port)
    server.startService()
    
    