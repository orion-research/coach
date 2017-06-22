"""
Created on 16 juin 2017

@author: francois
"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

from COACH.test.test_interaction_service.TestCreateOpenCase import TestCreateOpenCase
from COACH.test.test_interaction_service.TestLogin import TestLogin

import unittest

from COACH.test.Suite import Suite

# initialize the test suite
try:
    if sys.argv[1] == "-l":
        suite  = Suite(True)
    else:
        suite = Suite()
except IndexError:
    suite = Suite()

# add tests to the test suite
suite.addTests(unittest.makeSuite(TestCreateOpenCase))
# suite.addTests(unittest.makeSuite(TestLogin))

# initialize a runner, pass it your suite and run it
runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)