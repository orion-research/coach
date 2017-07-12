"""
Created on 16 juin 2017

@author: francois
"""

import unittest

import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH import launch_local

class Suite(unittest.TestSuite):
    
    def __init__(self, isServerLaunched = False):
        super().__init__(self)
        self.isServerLaunched = isServerLaunched
    
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