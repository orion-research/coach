'''
Created on 17 apr. 2016

@author: Jakob Axelsson
'''

import sys

from COACH.framework import coach

if __name__ == '__main__':
    coach.RootService("settings/root_settings.json", sys.argv[1:])
    coach.DirectoryService("settings/directory_settings.json")