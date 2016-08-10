'''
Created on 9 aug. 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach


class PughService(coach.DecisionProcessService):

    def process_menu(self):
        return "Hello, Pugh!"

if __name__ == '__main__':
    PughService(sys.argv[1]).run()