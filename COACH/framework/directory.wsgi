"""
wsgi file for the COACH directory service, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.DirectoryService(os.path.normpath("settings/directory_settings_development.json"), 
                                     working_directory = os.path.abspath(os.curdir)).ms
