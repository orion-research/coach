"""
Created on June 22, 2016

@author: Jan Carlson

The context model service
"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))


# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint, get_service, post_service

# Web server framework
from flask.templating import render_template



class ContextModelService(coach.Microservice):
# JC: Or should this be one specialization of a common ContextModel Service class defined in coach.py??? 

    @endpoint("/edit_context_dialogue", ["GET"])
    def edit_context_dialogue_transition(self, case_db, case_id):
        """
        Endpoint which lets the user edit context information.
        """
        context_text = get_service(case_db, "get_case_property", case_id = case_id, name = "context_text")
        return render_template("edit_context_dialogue.html", context_text = context_text)     

        
    @endpoint("/edit_context", ["POST"])
    def edit_context(self, case_db, case_id, context_text):
        """
        This method is called using POST when the user presses the save button in the edit_context_dialogue_transition.
        It gets several form parameters: 
        case_id : The ID of the current case
        context_text : The text entered in the main context text area
        It writes the new context information to the database, and then returns a status message to be shown in the main dialogue window.
        """
        # Write the new context information to the database.
        post_service(case_db, "change_case_property", case_id = str(case_id), name = "context_text", value = context_text)
        return "Context information saved. (" + context_text + ")"
    
if __name__ == '__main__':
    ContextModelService(sys.argv[1]).run()
