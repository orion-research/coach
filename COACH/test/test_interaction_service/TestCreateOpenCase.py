"""
Created on 16 juin 2017

@author: francois
"""

import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH.test.BaseTest import BaseTest
import COACH.framework.InteractionService

import unittest
from unittest import mock

import requests
from flask import request
import time

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

    
class TestCreateOpenCase(BaseTest):
    def setUp(self):
        super().setUp()
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid"}
        requests.request("POST", interactionService + "/login_user", params=loginInformation)
    
        
    @mock.patch("framework.InteractionService.flask")
    def test(self, mockSession):
        mockSession.return_value.side_effect = [1, 2, 3]
        interactionService = self.serviceAddress["InteractionService"]
        log("interactionService :", interactionService)
        createCaseInformation = {"title": "testCase", "description": "case description"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        log(response.text)
        log("list of mock's calls :", mockSession.return_value.call_args_list)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<H2>Case status</H2>" in response.text)
        log("caseId :", self.getCaseId())     
        
        
    def _testMoveToCreateCaseValid(self):
        interactionService = self.serviceAddress["InteractionService"]
        response = requests.request("GET", interactionService + "/create_case_dialogue")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<H1>Create new decision case</H1>" in response.text)
        self.assertTrue("Please fill title's field" not in response.text)
        self.assertTrue("Please fill description's field" not in response.text)
        
    def _testMoveToCreateCaseTooManyParameters(self):
        interactionService = self.serviceAddress["InteractionService"]
        response = requests.request("GET", interactionService + "/create_case_dialogue", params={"Unexpected": "parameter"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
    
    def _testMoveToCreateCaseInvalidMethod(self):
        interactionService = self.serviceAddress["InteractionService"]
        response = requests.request("POST", interactionService + "/create_case_dialogue")
        self.assertEqual(response.status_code, 403)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
    
    def _testMoveToCreateCaseUnlogged(self):
        interactionService = self.serviceAddress["InteractionService"]
        requests.request("GET", interactionService + "/logout")
        response = requests.request("GET", interactionService + "/create_case_dialogue")
        self.assertEqual(response.status_code, 401)
        self.assertTrue("<title>401 Unauthorized</title>" in response.text)
    
    def _testCreateCaseValid(self):
        interactionService = self.serviceAddress["InteractionService"]
        log("interactionService :", interactionService)
        createCaseInformation = {"title": "testCase", "description": "case description"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        log(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<H2>Case status</H2>" in response.text)
        log("caseId :", self.getCaseId())
        
    def _testCreateCaseInvalidParameterName(self):
        interactionService = self.serviceAddress["InteractionService"]
        createCaseInformation = {"invalidName": "testCase", "description": "case description"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
        
    def _testCreateCaseInvalidParameterNumber(self):
        interactionService = self.serviceAddress["InteractionService"]
        createCaseInformation = {"title": "testCase", "description": "case description", "thirdParameter": "thirdParameter"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
        
    def _testCreateCaseInvalidMethod(self):
        interactionService = self.serviceAddress["InteractionService"]
        createCaseInformation = {"title": "testCase", "description": "case description"}
        response = requests.request("GET", interactionService + "/create_case", params=createCaseInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
        
    def _testCreateCaseEmptyTitle(self):
        interactionService = self.serviceAddress["InteractionService"]
        createCaseInformation = {"title": "", "description": "case description"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        self.assertEqual(response.status_code, 400)
        self.assertTrue("<H1>Create new decision case</H1>" in response.text)
        self.assertTrue("Please fill title's field" in response.text)
        
    def _testCreateCaseUnlogged(self):
        interactionService = self.serviceAddress["InteractionService"]
        requests.request("GET", interactionService + "/logout")
        createCaseInformation = {"title": "testCase", "description": "case description"}
        response = requests.request("POST", interactionService + "/create_case", params=createCaseInformation)
        self.assertEqual(response.status_code, 401)
        self.assertTrue("<title>401 Unauthorized</title>" in response.text)
        
        
if __name__ == "__main__":
    log("TestCreateCase main")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCreateOpenCase)
    unittest.TextTestRunner().run(suite)   
    
    
    
    