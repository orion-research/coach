"""
Created on 15 juin 2017

@author: francois
"""
import unittest

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH.framework.coach import Microservice

import requests
from flask import request
import re

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

class BaseTest(unittest.TestCase, Microservice):

    def setUp(self):
        Microservice.__init__(self)
        self.defineServicesAddress()
        
    def defineServicesAddress(self):
        globalSettings = self.get_setting("object")
        usedService = ["InteractionService", "PropertyModelService"]
        self.serviceAddress = {}
        for useServiceName in usedService:
            useService = self.get_setting(useServiceName)
            self.serviceAddress[useServiceName] = (globalSettings["protocol"] + "://" + globalSettings["host"] + ":" 
                                                      + str(useService["port"]))
            
    def getCaseId(self):
        interactionService = self.serviceAddress["InteractionService"]
        response = requests.request("GET", interactionService + "/export_case_to_knowledge_repository")
        caseDescription = response.text.replace("&gt;", ">").replace("&lt;", "<")
        pattern = r"(<http://127\.0\.0\.1:5008/data#[0-9]*>) a <http://www\.orion-research\.se/ontology#Case>"
        match = re.search(pattern, caseDescription)
        log("caseId :", match.group(1))
        return match.group(1)
        
    
if __name__ == "__main__":
    log("BaseTest main")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BaseTest)
    unittest.TextTestRunner().run(suite)
    
    
    