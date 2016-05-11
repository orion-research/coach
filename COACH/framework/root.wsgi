"""
wsgi file for the COACH root service, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

sys.path.append(os.curdir)
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir))
# sys.path.append('/usr/lib/python3.4')
# sys.path.append('/usr/lib/python3.4/plat-x86_64-linux-gnu')
# sys.path.append('/usr/lib/python3.4/lib-dynload')
# sys.path.append('/usr/local/lib/python3.4/dist-packages')
# sys.path.append('/usr/lib/python3/dist-packages')

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.RootService(os.path.normpath("settings/root_settings_development.json"), 
                                os.path.normpath("settings/root_secret_data.json"),
                                working_directory = os.path.abspath(os.curdir)).ms
