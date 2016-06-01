"""
wsgi file for the COACH simple decision process, to make it useable from Apache.
The script should be in the same directory as the Python file it imports.
"""

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.decision_process.SimpleDecisionProcessService import SimpleDecisionProcessService

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = SimpleDecisionProcessService.SimpleDecisionProcessService(os.path.normpath("settings/decision_process_settings_development.json"),
                                                                        working_directory = os.path.abspath(os.curdir)).ms
