"""
Created on 16 juin 2017

@author: francois
"""

import unittest

import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH import launch_local
from COACH.test.test_interaction_service.TestCreateOpenCase import TestCreateOpenCase
from COACH.test.test_interaction_service.TestLogin import TestLogin

class Suite(unittest.TestSuite):
    
    def __init__(self, isServerLaunched = False):
        super().__init__(self)
        self.isServerLaunched = isServerLaunched
        
        # add tests to the test suite
        # self.addTests(unittest.makeSuite(TestCreateOpenCase))
        self.addTests(unittest.makeSuite(TestLogin))
    
    def run(self, result):
        self.setUpSuite()
        super().run(result)
        self.tearDownSuite()

    def setUpSuite(self):
        if not self.isServerLaunched:
            caseDatabase = launch_local.run_all()
            #case_graph = caseDatabase.graph
    
    def tearDownSuite(self):
        pass