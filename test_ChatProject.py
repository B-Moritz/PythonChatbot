# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 19:11:02 2022

@author: b-mor
"""

import unittest
from client import MsgAnalysis, Tags
import server
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
        
        # Assert that the message only has one tag
        self.assertEqual(len(joinObj.tags), 1)
        # Assert that the join tag is the first tag
        self.assertEqual(joinObj.tags[0], Tags.join)

        # Case: The message is a question
        questionMessage = "\nHost: How is the weather in Berlin?"
        questionObj = MsgAnalysis(questionMessage)
        questionObj.classifyMsg()
        # Assert that the questionObject is adding the weather tag.
        self.assertTrue(Tags.weather in questionObj.tags)
        # Assert that the questionObject has added the question tag
        self.assertTrue(Tags.question in questionObj.tags)
        # Assert that the location has been identified:
        self.assertEqual(questionObj.location, "Berlin", "The location was not identified")
        # Assert that the message is not taged as join
        self.assertFalse(Tags.join in questionObj.tags, "The join tag should not be added for questions.") 
        
        # Case: The message is a statement/suggestion
        statement = "\nUser: It is cold today!"
        statObj = MsgAnalysis(statement)
        statObj.classifyMsg()
        # Assert that the message is taged as a statement:
        self.assertTrue(Tags.statement in statObj.tags)
        # Assert that the message is not taged as question
        self.assertFalse(Tags.question in statObj.tags)
        # Assert that the message is taged with temperature
        self.assertTrue(Tags.temperature in statObj.tags)
        # Assert that the message is not taged with location
        self.assertFalse(Tags.location in statObj.tags)
        
        # Case: The message asks for an opinion
        opinion = "\nHost: How would you rate the weather today?"
        opiObj = MsgAnalysis(opinion)
        opiObj.classifyMsg()
        # Assert that the message is classified as opinion
        self.assertTrue(Tags.opinion in opiObj.tags, "The message should be taged as opinion.")
        self.assertTrue(Tags.weather in opiObj.tags, "The message should be taged with subject weather!")
        self.assertTrue(Tags.question in opiObj.tags, "The message should be taged as a question!")
        self.assertEqual(opiObj.location, "", "No location should be identified!")
        
        # Case: Is it sunny in Oslo?
        question = "\nUser: Is it sunny in Oslo?"
        questionObj = MsgAnalysis(question)
        questionObj.classifyMsg()
        # Assert that the message is classified as question
        self.assertTrue(Tags.question in questionObj.tags, "Should be a question, but was not taged.")
        self.assertEqual(questionObj.location, "Oslo", "The location was not identified.")
        self.assertTrue(Tags.weather in questionObj.tags, "Should have been taged as weather!")
    
    def test_YrInterface(self):
        # Create a test object of the WatherApi class
        testYr = yr.WeatherApi()
        
        # -- Test the getCoordinates method
        # Assert that the city was found.
        self.assertTrue(testYr.getCoordinates("Oslo"), "The city 'Oslo' should be in the list.")
        # Assert that the coordinates are as expected (Oslo)
        self.assertEqual(testYr.long, 10.7528, "The longitued was not correct for Oslo")
        self.assertEqual(testYr.lat, 59.9111, "The  latitued was not correct for Oslo")
        # Assert that the ValueError is thrown when the city is not in the list
        with self.assertRaises(ValueError):
            testYr.getCoordinates("test")
            
        # -- Test the httpRequest method
        
        
        
if __name__=='__main__':
    unittest.main()