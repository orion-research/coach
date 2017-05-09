"""
Created on May 9, 2017

@author: Jan Carlson

The property model service
"""

"""
TODO:



"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))


# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Web server framework
from flask.templating import render_template
from flask import request


class PropertyModelService(coach.Microservice):


    @endpoint("/properties_dialogue", ["GET"], "text/html")
    def properties_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which lets the user manage properties.
        """
        
        case_db_proxy = self.create_proxy(case_db)
        
        return render_template(
          "properties_dialogue.html")     
    
if __name__ == '__main__':
    PropertyModelService(sys.argv[1]).run()
