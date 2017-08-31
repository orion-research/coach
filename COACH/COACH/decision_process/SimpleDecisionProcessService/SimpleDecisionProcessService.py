
# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class SimpleDecisionProcessService(coach.DecisionProcessService):

    @endpoint("/process_menu", ["GET"])
    def process_menu(self):
        return "Automatically generated process menu for SimpleDecisionProcessService"
        
if __name__ == '__main__':
        SimpleDecisionProcessService().run()
