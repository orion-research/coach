# -*- coding: utf-8 -*-
"""
Created on Wed May 10 09:57:30 2017

@author: Markus Borg
"""

import unittest
import COACH.framework.InteractionService

class TestCreateUser(unittest.TestCase):
    SUT = None
    
    def setUp(self):
        self.SUT = InteractionService()
     
        
    def test_get_version(self):
        self.assertNotEqual(self.SUT.get_version(), "No version information available", "Invalid version number")
   
        
    def tearDown(self):
        print("Tear down")
    

if __name__ == '__main__':
    unittest.main()