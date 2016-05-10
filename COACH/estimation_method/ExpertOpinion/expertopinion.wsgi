"""
wsgi file for the COACH expert opinion estimation method, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.estimation_method.ExpertOpinion import ExpertOpinion

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = coach.EstimationMethodService(os.path.normpath("settings/expert_opinion_settings_development.json"), 
                                            handling_class = ExpertOpinion.ExpertOpinion,
                                            working_directory = os.path.abspath(os.curdir)).ms
