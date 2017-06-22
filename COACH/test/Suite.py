"""
Created on 16 juin 2017

@author: francois
"""

import unittest

import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH import launch_local

# TODO: to suppress
from datetime import datetime
import inspect

def log(*args):
    message = datetime.now().strftime("%H:%M:%S") + " : "
    message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg) + " "
    print(message)
    sys.stdout.flush()

class Suite(unittest.TestSuite):
    
    def __init__(self, isServerLaunched = False):
        super().__init__(self)
        self.isServerLaunched = isServerLaunched
    
    def run(self, result):
        self.setUpSuite()
        super().run(result)
        self.tearDownSuite()

    def setUpSuite(self):
        log("SetUpSuite")
        if not self.isServerLaunched:
            caseDatabase = launch_local.run_all()
            log("caseDatabase :", caseDatabase)
            #case_graph = caseDatabase.graph
            #log(case_graph.serialize(format = "n3").decode("utf-8"))
            log("launch local finished")
    
    def tearDownSuite(self):
        log("TearDownSuite")
        pass