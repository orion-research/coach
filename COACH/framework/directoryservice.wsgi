# This file was automatically generated by the C:/Users/Jakob Axelsson/Documents/Arbetsdokument/Eclipse workspace/COACH/COACH/build_coach_deployments.py script on <module 'datetime' from 'C:\\Users\\Jakob Axelsson\\AppData\\Local\\Programs\\Python\\Python36\\lib\\datetime.py'>.
        
# wsgi file for the COACH DirectoryService microservice, to make it useable from Apache.
# The script should be in the same directory as the Python file it imports.

import os
import sys

sys.path.append("/var/www/COACH/COACH/framework")
sys.path.append("/var/www/COACH")

from COACH.framework.DirectoryService import DirectoryService


if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = DirectoryService().ms
