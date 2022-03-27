# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 19:11:02 2022

@author: b-mor
"""

import unittest
from client import MsgAnalysis, Tags, WeatherBot
import YrInterface as yr

class testClientModule(unittest.TestCase):
    
    def test_MsgAnalysis(self):
        '''
        This method contains the unit test of the MsgAnalysis class in clien.py.
        '''
        # Stage one: the initialization of an MsgAnalysis object is tested
        
        # Case: The argument is the wrong type
        arg = 10
        with self.assertRaises(TypeError):
            MsgAnalysis(arg)
        # case: Too complicated message
        complicatedMessage = "User: This is a test. Please treat this as a test."
        with self.assertRaises(ValueError):
            MsgAnalysis(complicatedMessage)
        
        # Stage two: the classification (classifyMsg() method) of the message is tested
        
        # Case: The message contains a join message
        joinMessage = "\nUser Testuser has joined the chat!"
        joinObj = MsgAnalysis(joinMessage)
        joinObj.classifyMsg()
        
        # Check that the message only has one tag
        self.assertEqual(len(joinObj.tags), 1)
        # Check that the join tag is the first tag
        self.assertEqual(joinObj.tags[0], Tags.join)

        # Case: The message is a question
        questionMessage = "\nHost: How is the weather in Berlin?"
        questionObj = MsgAnalysis(questionMessage)
        questionObj.classifyMsg()
        # Check that the questionObject is adding the weather tag.
        self.assertTrue(Tags.weather in questionObj.tags)
        # Check that the questionObject has added the question tag
        self.assertTrue(Tags.question in questionObj.tags)
        # Check that the location has been identified:
        self.assertEqual(questionObj.location, "Berlin", "The location was not identified")
        # Check that the message is not taged as join
        self.assertFalse(Tags.join in questionObj.tags, "The join tag should not be added for questions.") 
        
        # Case: The message is a statement/suggestion
        statement = "\nUser: It is cold today!"
        statObj = MsgAnalysis(statement)
        statObj.classifyMsg()
        # Check that the message is taged as a statement:
        self.assertTrue(Tags.statement in statObj.tags)
        # Check that the message is not taged as question
        self.assertFalse(Tags.question in statObj.tags)
        # Check that the message is taged with temperature
        self.assertTrue(Tags.temperature in statObj.tags)
        # Check that the message is not taged with location
        self.assertFalse(Tags.location in statObj.tags)
        
        # Case: The message asks for an opinion
        opinion = "\nHost: How would you rate the weather today?"
        opiObj = MsgAnalysis(opinion)
        opiObj.classifyMsg()
        # Control that the message is classified as opinion
        self.assertTrue(Tags.opinion in opiObj.tags, "The message should be taged as opinion.")
        self.assertTrue(Tags.weather in opiObj.tags, "The message should be taged with subject weather!")
        self.assertTrue(Tags.question in opiObj.tags, "The message should be taged as a question!")
        self.assertEqual(opiObj.location, "", "No location should be identified!")
        
        # Case: Is it sunny in Oslo?
        question = "\nUser: Is it sunny in Oslo?"
        questionObj = MsgAnalysis(question)
        questionObj.classifyMsg()
        # Control that the message is classified as question
        self.assertTrue(Tags.question in questionObj.tags, "Should be a question, but was not taged.")
        self.assertEqual(questionObj.location, "Oslo", "The location was not identified.")
        self.assertTrue(Tags.weather in questionObj.tags, "Should have been taged as weather!")
    
    def test_YrInterface(self):
        """
        This method tests the WeatherApi class.
        """
        # Create a test object of the WatherApi class
        testYr = yr.WeatherApi()
        
        # -- Test the getCoordinates method
        # Check that the city was found.
        self.assertTrue(testYr.getCoordinates("Oslo"), "The city 'Oslo' should be in the list.")
        # Check that the coordinates are as expected (Oslo)
        self.assertEqual(testYr.long, 10.7528, "The longitued was not correct for Oslo")
        self.assertEqual(testYr.lat, 59.9111, "The  latitued was not correct for Oslo")
        # Control that the ValueError is thrown when the city is not in the list
        with self.assertRaises(ValueError):
            testYr.getCoordinates("test")
            
        # -- Test the getCurrentWeatherData method
        testYr = yr.WeatherApi()
        # Control that the method raises TypeError if city is not a string
        with self.assertRaises(TypeError):
            testYr.getCurrentWeatherData(10)
        # Check that the method raises ValueError if the city is not known
        with self.assertRaises(ValueError):
            testYr.getCurrentWeatherData("test")
            
        d1, d2 = testYr.getCurrentWeatherData("Oslo")

        self.assertTrue(type(d1) == float and type(d2) == float, 
                        "Error in the return data of getCurrentWeatherData.")
            
        # -- Test the conversion methods
        # Check that the input validation is working
        with self.assertRaises(TypeError): 
            testYr.convertCloudArea("test")
        
        with self.assertRaises(RuntimeError):
            testYr.convertCloudArea(float(110))
           
        # Control that the method returns the right word for different input fractions
        self.assertEqual(testYr.convertCloudArea(10.0), "wery cloudy")
        self.assertEqual(testYr.convertCloudArea(25.0), "cloudy")
        self.assertEqual(testYr.convertCloudArea(50.0), "partially cloudy")
        self.assertEqual(testYr.convertCloudArea(75.0), "clear")
        self.assertTrue(type(testYr.convertCloudArea(d2)) == str, f"The fraction {d2} from \
                        getCurrentTemperatureData could not be processed by convertCloudArea.")
        
        # Control the convertTemperature() method
        with self.assertRaises(TypeError):
            testYr.convertTemperature("test")
        
        with self.assertRaises(ValueError):
            testYr.convertTemperature(-300.0)
        # Check that the convert temperature method returns the correct word
        self.assertEqual(testYr.convertTemperature(30.0), "hot")
        self.assertEqual(testYr.convertTemperature(20.0), "not cold")
        self.assertEqual(testYr.convertTemperature(10.0), "cold")
        self.assertEqual(testYr.convertTemperature(-1.0), "wery cold")
        self.assertTrue(type(testYr.convertTemperature(d1)) == str)
    
    def test_weatherBot(self):
        """
        This method tests the WeatherBot class. It is important that the 
        MsgAnalysis class and WeatherApi class are working since the 
        WeatherBot class is dependant those classes. 
        """
        # Get the weather data for Oslo
        testYr = yr.WeatherApi()
        airTemp, cloud = testYr.getCurrentWeatherData("Oslo")
        # Create a test bot
        bot = WeatherBot("192.168.56.1", 2020)
        
        # Test qustion about temperature -----
        bot.recvQueue.put("\nHost: What is the temperature in Oslo?")
        # Process the question
        bot.generateResponse()
        # The expected response from the bot
        expectedResponse = ("The temperature in Oslo is " + str(airTemp) + 
                            " degree celcius!\n Information is based on data from MET Norway.")
        
        realResponse = bot.sendQueue.get()
        # Check that the response generated is correct.
        self.assertEqual(realResponse, expectedResponse)
        
        # Test question about the weather
        bot.recvQueue.put("\nHost: How is the weather in Oslo?")
        # Process the question.
        bot.generateResponse()
        # The expected response from the bot
        expectedResponse = ("The temperature in " + "Oslo" + 
                          " is " + str(airTemp) + " degree celcius! The sky is " + 
                          testYr.convertCloudArea(cloud) + 
                          ".\n Information is based on data from MET Norway.")
        realResponse = bot.sendQueue.get()
        # Check that the response is correct  
        self.assertEqual(realResponse, expectedResponse)
        
        # Test request for opinion about the weather (with location) ----
        bot.recvQueue.put("\nUser: Do you like the weather in Oslo?")
        # pricess the question
        bot.generateResponse()
        # The exptected response from the bot
        expectedResponse = ("The weather in " + "Oslo" + 
                           " is " + testYr.convertCloudArea(cloud) + 
                           " and " + testYr.convertTemperature(airTemp) + ". " + 
                           ("I like it!" if airTemp > 15 and cloud < 10 else "I do not like it!") + 
                           "\n Information is based on data from MET Norway.")
        realResponse = bot.sendQueue.get()
        # Check that the response from the bot is correct
        self.assertEqual(realResponse, expectedResponse)
        
        
        
        
        
        
        
if __name__=='__main__':
    unittest.main()