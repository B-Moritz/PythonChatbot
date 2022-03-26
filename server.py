# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 00:50:00 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

The module server is part of the solution to the individual 
portfolio assignemnt in the course DATA2410 - Datanetwerk 
og skytjenester. The module contains the classes used to 
host the single threaded chat service. This includes handeling 
TCP connections from users, receiving messages from users and 
forwarding them to all other users.

The module consists of two classes. One is the HostBot class. This 
class simulates the host user which is initiating conversations 
periodically. 
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
from datetime import datetime

class HostBot:
    """
    This class represents the host which is initiating conversations 
    in the chat thread. The method hostThread in the SimpleChatServer
    class is dependant on this class.
    The messages which are sent from the host are saved in the 
    conversationInitiators.txt in the same forlder as the server.py 
    file.
    """
    # The contstant defining the period a message should be active (seconds)
    MESSAGE_LIFETIME = 60
    def __init__(self):
        # The messages that could be sent by the host, are read from file 
        try:
            with open(".\\conversationInitiators.txt", "r") as file:
                self.conversationInitiators = file.read().split("\n")
            
            # Empty lines are removed
            while self.conversationInitiators[-1] == '':
                # While there is an empty string at the end of the list
                # -> remove the empty string
                self.conversationInitiators.pop()
            
            if len(self.conversationInitiators) == 0:
                raise RuntimeError
        except (FileNotFoundError, RuntimeError):
            # If the file was not found or has no content
            # -> write error to the log and add a default message to conversationInitiators
            logging.error("The file, conversationInitiators.txt, was not found!")
            self.conversationInitiators = ["What is the temperature in Oslo?"]
        
        # A message is set as the current message to be sent
        self.setCurInit()
        
    
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
            self.setCurInit()
            # The current message is returned
        return self.curInit
    
    def setCurInit(self):
        """
        This method sets the current message and stores the start time of 
        the message.

        Returns
        -------
        None.

        """
        # A new message is set
        self.curInit = random.choice(self.conversationInitiators)
        # The start time of the message is captured
        self.msgStartTime = time.time()

class SimpleChatServer:
    """
    
    """
    event = threading.Event()
    userInteractionEvent = threading.Event()
    history = []
    # End of message code used to identify the end of each message sent between the server and the user
    END_OF_MSG = "::EOMsg::"
    # The maximal number of bytes received per receive sycle 
    MAX_RCV = 100
    botnamePattern = re.compile("^(.*): ")
    HOSTBOT_UNAME = "Host"
    # The time between host messages (seconds)
    HOST_PERIOD = 90
    # The main part of the kick message
    KICK_MSG = "Kicked by the host for "
    
    cmdPattern = re.compile("^([^ ]*) {0,1}(.*)$")
    
    def __init__(self, port):
        if type(port)!=int or port < 0 or port > 65535:
            raise ValueError(f"The provided port {port} is not valid. \
                             Please provide a decimal number between 0 and 65535")
        
        self.port = port
        self.isRunning = False
        self.sendQueues = {}
        self.checkReadable = []
        self.checkWritable = []
        self.checkError = []
        self.recvRest = {}
        self.closeNext = []
        self.activeThreads = Queue()
        self.finishRemovalList = []
        # Defining the command set with commands used to controll the service
        self.cmdSet = {"listConnections" : ["Prints a list of all connected users. ", 
                                         "The command takes no arguments.", self.listConnections], 
                       "kick": ["Disconnects a specified user from the server. ", 
                                "The command takes two arguments: username of the user (mandatory) " +
                                "and the reason for the kick (optional). The reason can be given " +
                                "as a space separated words. Eks: kick User Due to service overload.", self.kickUser],
                       "exit" : ["Stops the chat service. ", "The comamnd takes no arguments.", self.stopService]}
        
        
    def startService(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind(('', self.port))
        self.serverSocket.listen(5)
        self.checkReadable.insert(0, self.serverSocket) 
        
        logging.info("Service is listening to incomming connections on port %s.", str(self.port))
        print("Python Chat service\tCreated by Bernt Olsen, student at OsloMet.\n")
        print("Service is listening to incomming connections on port {}. \n".format(str(self.port)))
        self.isRunning = True
        
        mainThread = threading.Thread(target=self.mainThread)
        mainThread.start()
        
        # List the commandset
        print(self.listCommands())
        
        while not self.userInteractionEvent.is_set():
            cmd = input("\033[92mHost\033[0m $> ")
            # Extract the command and arguments
            matchResult = self.cmdPattern.search(cmd)
            
            if bool(matchResult):
                cmd = matchResult.groups()[0] # command
                arguments = matchResult.groups()[1].split(" ") # arguments
                if cmd in self.cmdSet:
                    # If the command is recognized, check the  arguments
                    if cmd == "kick":
                        reason = ""
                        # Check the arguments if the kick command is given
                        if len(arguments) == 0 or arguments[0] == '':
                            print("No username was specified. Please specify the username \
                                  of the user that should be removed.")
                        elif len(arguments) == 1:
                            username = arguments[0]
                        else:
                            reason = arguments[1]
                            for word in arguments[2:]:
                                reason += " " + word
                        
                        # Run the kick method     
                        if not self.cmdSet[cmd][2](username, reason):
                            print(f"User with username {username} was not found!")
                        else:
                            print(f"User {username} was removed!")
                    else:
                        # Execute method associated with the command
                        self.cmdSet[cmd][2]()
                else: 
                   print(f"The command {cmd} was not recognized!")
        
        waitGraphicsThread = threading.Thread(target=self.waitIndication, args=(mainThread,))
        waitGraphicsThread.start()
        mainThread.join()
        self.serverSocket.close()
        self.isRunning = False
        waitGraphicsThread.join()
        print("Service stopped successfully!")
        
    def mainThread(self):
        
        hostbotThread = threading.Thread(target=self.hostbotThread, daemon=True)
        hostbotThread.start()

        
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
            
            while len(self.finishRemovalList) != 0:
                self.finishRemoval(self.finishRemovalList.pop())
            
            while len(err) != 0:
                self.removeClient(err.pop())
                
                
            while len(self.closeNext) != 0:
                self.removeClient(self.closeNext.pop())
        
        hostbotThread.join(1)
            
    def hostbotThread(self):
        """
        This method is the target of the hostThread object from the main thread 
        and contains the routin which is run by the hostThread. The routine 
        instantiates a HostBot object, gets the message set by the HostBot 
        and sends puts it in each send queue. This is repeated in a cycle with 
        the length given by the HOST_PERIOD constant. The thread ends when the 
        event flag is set.
        
        Returns
        -------
        None.

        """
        # An HostBot object is instantiated
        self.hostbot = HostBot()
        
        while not self.event.is_set():
            # While the event flag is not set
            logging.info("A new message is sent from host")
            # Get the current message set by the HostBot object
            msg = f"{self.HOSTBOT_UNAME}: {self.hostbot.getCurMsg()}"
            # Add the message to the thread cache
            self.history.append(msg)

            for queue in self.sendQueues.values():
                # Add the message to each send queue
                queue[0].put(msg)
            # Put the thread in idle for the given amount of seconds (HOST_PERIOD)
            time.sleep(self.HOST_PERIOD)
            
    def acceptConnection(self):
        client, src = self.serverSocket.accept()
        logging.info(f"New client connection accepted for source {src}.")
        logging.info(f"History added to sendQueue of the new connection: {str(self.history)}")        
        curQueue = Queue()
        for i in range(len(self.history)):
            curQueue.put(self.history[i])
            
        # sendQueues is a dictionary that contains variables for each connected 
        # user socket. Format:
        # {client.getpeername() : [sendQueue, rest_from_last_receive, "username", time_last_received_msg, Kick_reason, socketObject
        self.sendQueues[client.getpeername()] = [curQueue,          #0 sendQueue
                                                 "",                #1 rest from last receive
                                                 "",                #2 username
                                                 datetime.now(),    #3 timestamp last receive
                                                 "",                #4 kick_reason
                                                 client]            #5 socket Object
        
        self.checkReadable.append(client)
        self.checkWritable.append(client)
        self.checkError.append(client)
    
    def sendToClient(self, cliSock):
        
        sendQueue = self.sendQueues[cliSock.getpeername()][0]
        
        for i in range(sendQueue.qsize()):
            sendMsg = sendQueue.get()
            logging.info(f"Sending {sendMsg} to {cliSock.getpeername()}")
            msg = (sendMsg + self.END_OF_MSG).encode()
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
        logging.info(f"Receiving from client {cliSock.getpeername()}")
        # Compiling a pattern for matching end of message
        pattern = re.compile(self.END_OF_MSG)
        # Gets an address to the list of important variables for the given socket 
        clientVariables = self.sendQueues[cliSock.getpeername()]
        # Extracts the rest of the previous reception. This variable contains 
        # a non empty string whenever the previous reception received a portion of the next message 
        # in the same process.
        data_recv = clientVariables[1]
        # Definition of a variable for the new data
        cur_recv = ""
        
        while not bool(pattern.search(data_recv)) and len(data_recv) < self.MAX_RCV: 
            # While the received data does not contain the end of message code
            # or the received data does not exceed the maximal size, continue 
            # reading from buffer.
            try:
                # Read from the buffer of the client socket
                cur_recv = cliSock.recv(1024).decode()
            except (ConnectionAbortedError, ConnectionResetError) as E:
                logging.warning(f"The connection with the client {cliSock.getpeername()} has ended: {E}")
                # Queue the socket for termination and end the receive thread.
                self.closeNext.append(cliSock)
                return
                
            if len(cur_recv) == 0:
                # If the recv method returned nothing, then the connection is closed.
                # The data that was sent before an EOMsg was found will be dropped
                logging.warning(f"Server is not receiving from {cliSock.getpeername()}. Connection is closing!")
                # Queue the socket for termination and end the receive thread.
                self.closeNext.append(cliSock)
                return
            
            # The received data is added to the data from the previous receive cycle
            data_recv = data_recv + cur_recv
        
        logging.info(f"Data received: {data_recv}")
        # Saving the timestamp for the receive:
        self.sendQueues[cliSock.getpeername()][3] = datetime.now()
        # Cleaning up the received data and create a list of all messages 
        # contained in the received message 
        msgList = data_recv.replace("\n", "").split(self.END_OF_MSG)
        # The last message in the list is stored ('' if the last messsage is complete)
        self.sendQueues[cliSock.getpeername()][1] = msgList.pop()
        
        if clientVariables[2] == "":
            # If there is no username registered for the socket, then 
            # the message must be the first message (connection message), 
            # containing only the username
            clientVariables[2] = msgList[0][msgList[0].find(":") + 2 : ]
            # Send a join message to all clients
            self.populateSendQues(f"\nUser {clientVariables[2]} has joined the chat!", cliSock)
        else:
            # The message is processed as a chat message if the username is set
            for msg in msgList:
                # All messages are forwarded to the other sockets
                self.populateSendQues(msg, cliSock)
    
    def populateSendQues(self, msg, cliSock):
        """
        This method is adding a message to the send queues of each client socket, 
        except the socket given as argument to this method (cliSock). The message 
        is also provided as argument (msg).
        """
        # Add the message to the chat history
        self.history.append(msg)
        for key in self.sendQueues.keys():
            # For each send client socket check that the socket is not the socket 
            # provided as argument to this method.
            if key != cliSock.getpeername():     
                # Add the message in the send queue
                self.sendQueues[key][0].put(msg)
                
    def removeClient(self, cliSock):
        logging.info(f"The connection to {cliSock.getpeername()} is closing.")
        uname = self.sendQueues[cliSock.getpeername()][2]
        self.populateSendQues(f"{uname}: User {uname} left the chat.\n", cliSock)
        # Remove socket from the list of readable sockets to avoid receiving from the client
        self.checkReadable.remove(cliSock)
        # The socket is also removed from the list for error checking
        self.checkError.remove(cliSock)
        # Add the disconnect message to the clients sendQueue
        reason = self.sendQueues[cliSock.getpeername()][4]
        discMessage = self.KICK_MSG + reason
        self.sendQueues[cliSock.getpeername()][0].put(discMessage)
        # Add the socket to the list of sockets which are in the removal process
        self.finishRemovalList.append(cliSock) 
    
    def finishRemoval(self, cliSock):
        """
        This method finishies the removal of a socket. 
        It is required that the removeClient method has been 
        called for the same socket first.
        """
        self.sendQueues.pop(cliSock.getpeername())
        cliSock.close()
        self.checkWritable.remove(cliSock)
        
    def listConnections(self):
        """
        This method creates a list of all the connected users 
        and prints the list to the terminal
        """
        
        outString = "{:>15}{:>20}{:>30}\n".format("Username", "IPv4 Address/Port", "Time last received")
        outString += "{:>15}{:>20}{:>30}\n".format("--------", "--------", "--------")
        for connection in self.sendQueues.keys():
            portAndAddress = str(connection[0]) + ":" + str(connection[1])
            username = self.sendQueues[connection][2]
            lastReceived = str(self.sendQueues[connection][3])
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
        for clientList in self.sendQueues.values():
            # For each list in the connection dictionary
            if clientList[2] == username:
                # If the list contains the username 
                # then add the socket in the same list to the closeNext list
                # in order to initiate its removal.
                self.closeNext.append(clientList[5])
                # Return true to confirm that the client is removed
                logging.info(f"User {username} is removed with the following reason: {reason}")
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
    
    def stopService(self):
        """
        This method removes all connections and stops the chat service
        """
        print("  Service is shutting down.", end="\r")
        logging.info("The service is stoping due to user interaction.")
        # End the user interaction loop.
        self.userInteractionEvent.set()
        # Remove the server socket from the check receivable list to avoid new connections
        self.checkReadable.pop(0)
        # Add all sockets to the close next list
        for clientSocket in self.checkReadable:
            self.closeNext.append(clientSocket)
        
        while len(self.sendQueues.keys()) > 0:
            # Wait until all connections are removed
            time.sleep(1)
        # Set the event flag in order to stop the program
        self.event.set()
    
    def waitIndication(self, mainThread):
        while mainThread.is_alive():
            print("-", "\r", end="")
            time.sleep(0.1)
            print("\\", "\r", end="")
            time.sleep(0.1)
            print("|", "\r", end="")
            time.sleep(0.1)
            print("/", "\r", end="")
            time.sleep(0.1)

if __name__=="__main__":
    
    #Handle command line argument
    parser = argparse.ArgumentParser(description="This program starts a sigle threaded chat service.")
    parser.add_argument('-p', '--Port', nargs='?', default=2020, metavar="PORT",
                        type=int, help="The port number associated with the service")
    args = parser.parse_args()
    
    logDay = f"{datetime.now().date().__str__()}"
    logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s', 
                        filename=f"./Logs/chatServer_{logDay}.log", level=logging.INFO)
    
    server = SimpleChatServer(args.Port)
    server.startService()
    
    