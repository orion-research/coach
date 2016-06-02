"""
wsgi file for the COACH expert opinion estimation method, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

# Activate virtual environment
activate_this = '/var/www/developmentenv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.append("/var/www/COACH/COACH/estimation_method/ExpertOpinion")
sys.path.append("/var/www/COACH")


from COACH.estimation_method.ExpertOpinion import ExpertOpinion

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.EstimationMethodService(os.path.normpath("/var/www/COACH/COACH/development_settings.json"), 
                                            handling_class = ExpertOpinion.ExpertOpinion,
                                            working_directory = "/var/www/COACH/COACH/estimation_method/ExpertOpinion").ms
