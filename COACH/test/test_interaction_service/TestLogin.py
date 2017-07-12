"""
Created on 15 juin 2017

@author: francois
"""
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH.test.BaseTest import BaseTest

import unittest

import requests
from flask import request

class TestLogin(BaseTest):
    
    def testValidLogin(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<title>COACH decision support system</title>" in response.text)
    
    def testInvalidUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" in response.text)
        self.assertTrue("Error: User name or password missing!" not in response.text)

    def testInvalidPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" in response.text)
        self.assertTrue("Error: User name or password missing!" not in response.text)
        
    def testInvalidUserIdAndPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" in response.text)
        self.assertTrue("Error: User name or password missing!" not in response.text)
        
    def testEmptyUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: User name or password missing!" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" not in response.text)
        
    def testEmptyUserIdAndInvalidPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: User name or password missing!" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" not in response.text)
        
    def testEmptyPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: User name or password missing!" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" not in response.text)
        
    def testEmptyPasswordAndInvalidUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: User name or password missing!" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" not in response.text)
        
    def testEmptyUserIdAndPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<TITLE>COACH</TITLE>" in response.text)
        self.assertTrue("Error: User name or password missing!" in response.text)
        self.assertTrue("Error: Wrong password, or user does not exist, or has not been confirmed!" not in response.text)

    def testInvalidRequestMethod(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)

    def testInvalidParameterName(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"invalid_parameters": "valid", "password": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
        
    def testTooManyParameters(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid", "third_parameter": ""}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)
        
    def testMissingParameter(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertTrue("<title>405 Method Not Allowed</title>" in response.text)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLogin)
    unittest.TextTestRunner().run(suite)      
    
      