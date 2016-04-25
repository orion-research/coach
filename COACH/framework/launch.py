'''
Created on 17 apr. 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir))


# from COACH.framework import coach
import coach

if __name__ == '__main__':
    coach.RootService(sys.argv[1], sys.argv[3:])
    coach.DirectoryService(sys.argv[2])
