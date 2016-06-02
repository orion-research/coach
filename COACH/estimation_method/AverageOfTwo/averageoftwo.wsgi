"""
wsgi file for the COACH average of two estimation method, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

# Activate virtual environment
activate_this = '/var/www/developmentenv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.append("/var/www/COACH/COACH/estimation_method/AverageOfTwo")
sys.path.append("/var/www/COACH")


from COACH.estimation_method.AverageOfTwo import AverageOfTwo

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.EstimationMethodService("/var/www/COACH/COACH/development_settings.json", 
                                            handling_class = AverageOfTwo.AverageOfTwo,
                                            working_directory = "/var/www/COACH/COACH/estimation_method/AverageOfTwo").ms
