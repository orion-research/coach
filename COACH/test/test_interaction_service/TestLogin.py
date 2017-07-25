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

LOGIN_TITLE = "<title>COACH</title>"
MAIN_MENU_TITLE = "<title>COACH decision support system</title>"
METHOD_NOT_ALLOWED_TITLE = "<title>405 Method Not Allowed</title>"

MISSING_USER_NAME_OR_PASSWORD = "Error: User name or password missing!"
USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD = "Error: Wrong password, or user does not exist, or has not been confirmed!"


class TestLogin(BaseTest):
    
    def testValidLogin(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(MAIN_MENU_TITLE, response.text)
    
    def testInvalidUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertNotIn(MISSING_USER_NAME_OR_PASSWORD, response.text)

    def testInvalidPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertNotIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testInvalidUserIdAndPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertNotIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testEmptyUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": "valid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertNotIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testEmptyUserIdAndInvalidPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": "invalid"}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertNotIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testEmptyPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertNotIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testEmptyPasswordAndInvalidUserId(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "invalid", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertNotIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertIn(MISSING_USER_NAME_OR_PASSWORD, response.text)
        
    def testEmptyUserIdAndPassword(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "", "password": ""}
        response = requests.request("POST", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 200)
        self.assertIn(LOGIN_TITLE, response.text)
        self.assertNotIn(USER_DOES_NOT_EXIST_OR_WRONG_PASSWORD, response.text)
        self.assertIn(MISSING_USER_NAME_OR_PASSWORD, response.text)

    def testInvalidRequestMethod(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertIn(METHOD_NOT_ALLOWED_TITLE, response.text)

    def testInvalidParameterName(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"invalid_parameters": "valid", "password": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertIn(METHOD_NOT_ALLOWED_TITLE, response.text)
        
    def testTooManyParameters(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid", "password": "valid", "third_parameter": ""}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertIn(METHOD_NOT_ALLOWED_TITLE, response.text)
        
    def testMissingParameter(self):
        interactionService = self.serviceAddress["InteractionService"]
        loginInformation = {"user_id": "valid"}
        response = requests.request("GET", interactionService + "/login_user", params=loginInformation)
        self.assertEqual(response.status_code, 405)
        self.assertIn(METHOD_NOT_ALLOWED_TITLE, response.text)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLogin)
    unittest.TextTestRunner().run(suite)      
    
      