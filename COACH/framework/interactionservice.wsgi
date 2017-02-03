# This file was automatically generated by the C:\Users\Jakob Axelsson\Documents\Arbetsdokument\Eclipse workspace\COACH\COACH\build_coach_deployments.py script on <module 'datetime' from 'C:\\Python34\\lib\\datetime.py'>.
        
# wsgi file for the COACH InteractionService microservice, to make it useable from Apache.
# The script should be in the same directory as the Python file it imports.

import os
import sys

# Activate virtual environment
activate_this = '/var/www/developmentenv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.append("/var/www/COACH/COACH/framework")
sys.path.append("/var/www/COACH")

from COACH.framework.InteractionService import InteractionService


if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = InteractionService(os.path.normpath("/var/www/COACH/COACH/development_settings.json"),
                                        os.path.normpath("/var/www/COACH/COACH/framework/settings/root_secret_data.json"),
                                        working_directory = os.path.abspath("/var/www/COACH/COACH/framework")).ms