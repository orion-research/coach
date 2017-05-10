# -*- coding: utf-8 -*-
"""
Created on Wed May 10 09:57:30 2017

Make sure to close all running instances of COACH before running the tests.

@author: Markus Borg
"""

import unittest
import random
import string
from COACH import launch_local
from COACH.framework import coach

class TestCreateUser(unittest.TestCase):
    int_service_proxy = None
    auth_service_proxy = None
    localhost = "http://127.0.0.1"
    int_port = ":5000" #:443 for remote server
    auth_port = ":5009"


    def setUp(self):
        launch_local.run_all()
        self.int_service_proxy = coach.Proxy(self.localhost + self.int_port, ["POST", "GET"])
        self.auth_service_proxy = coach.Proxy(self.localhost + self.auth_port, ["POST", "GET"])


    def test_get_version(self):
        self.assertNotEqual(self.int_service_proxy.get_version(), "No version information available", "Invalid version number")


    def test_create_user_wrong_repeated_password(self):
        http_response = self.int_service_proxy.create_user(user_id = "Test",
                                                           password1 = "pw1",
                                                           password2 = "pw2",
                                                           name = "Full Name",
                                                           email = "orion@ri.se")
        self.assertIn("Error: Password and repeated password not equal!", http_response,
                      "COACH did not notice wrong repeated password")


    def test_create_random_user(self):
        password = self.get_random_string(8)
        http_response = self.int_service_proxy.create_user(user_id = self.get_random_string(6),
                                                           password1 = password,
                                                           password2 = password,
                                                           name = self.get_random_string(10),
                                                           email = self.get_random_string(5) + "@ri.se")
        self.assertIsNotNone(http_response, "No HTTP response when creating new user")


    def tearDown(self):
        print("Tear down")

    def get_random_string(self, length):
        return "".join([random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
                        for _ in range(0, length)])


if __name__ == '__main__':
    unittest.main()