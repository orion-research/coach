"""
wsgi file for the COACH average of two estimation method, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.estimation_method.AverageOfTwo import AverageOfTwo

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.EstimationMethodService(os.path.normpath("settings/average_of_two_settings_development.json"), 
                                            handling_class = AverageOfTwo.AverageOfTwo,
                                            working_directory = os.path.abspath(os.curdir)).ms
