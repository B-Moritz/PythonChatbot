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
        
        # case: The argument is the wrong type
        arg = 10
        with self.assertRaises(TypeError):
            MsgAnalysis(arg)
        # case: Too complicated message
        complicatedMessage = "This is a test. Please treat this as a test."
        with self.assertRaises(ValueError):
            MsgAnalysis(complicatedMessage)
        
        # Stage two: the classification (classifyMsg() method) of the message is tested
        
        # case: The message contains a join message
        joinMessage = "User Testuser has joined the chat!"
        joinObj = MsgAnalysis(joinMessage)
        joinObj.classifyMsg()
        
        # Assert that the message only has one tag
        self.assertEquals(len(joinObj.tags), 1)
        # Assert that the join tag is the first tag
        self.assertEquals(joinObj.tags[0], Tags.join)

        # case: The message is a question
        questionMessage = "How is the weather in Berlin?"
        questionObj = MsgAnalysis(questionMessage)
        questionObj.classifyMsg()
        # Assert that the questionObject is adding the weather tag.
        self.assertTrue(Tags.weather in questionObj.tags)
        # Assert that the questionObject has added the question tag
        self.assertTrue(Tags.question in questionObj.tags)
        
if __name__=='__main__':
    unittest.main()