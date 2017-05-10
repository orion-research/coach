# -*- coding: utf-8 -*-
"""
Created on Wed May 10 09:57:30 2017

Make sure to close all running instances of COACH before running the tests.

@author: Markus Borg
"""

import unittest
from COACH import launch_local
from COACH.framework import coach

class TestCreateUser(unittest.TestCase):
    int_service_proxy = None
    dummyUser = None
    url = "http://127.0.0.1:5000" #use 127.0.0.1:443 for remote server
    
    def setUp(self):
        launch_local.run_all()
        self.int_service_proxy = coach.Proxy(self.url, ["POST", "GET"])


    def test_get_version(self):
        self.assertNotEqual(self.int_service_proxy.get_version(), "No version information available", "Invalid version number")

        
    def test_create_user(self):
        a = 3
   
        
    def tearDown(self):
        print("Tear down")
    

if __name__ == '__main__':
    unittest.main()