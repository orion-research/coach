"""
Created on 16 juin 2017

@author: francois
"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

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

runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)