"""
wsgi file for the COACH root service, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

from COACH.framework import coach

#    if len(sys.argv) != 4:
#        print("Usage: python launch.py <neo4j user name> <neo4j password> <password hash key>")
#        exit(1)

# TODO: How handle the secret command line arguments???
 
application = 
    coach.RootService(os.path.normpath("settings/root_settings_local.json"), 
                      os.path.normpath("settings/root_secret_data.json"),
                      working_directory = os.path.abspath(os.curdir))
