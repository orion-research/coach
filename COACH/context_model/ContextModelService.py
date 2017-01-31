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
from COACH.framework.coach import endpoint

# Web server framework
from flask.templating import render_template
from flask import request


class ContextModelService(coach.Microservice):
# JC: Or should this be one specialization of a common ContextModel Service class defined in coach.py??? 

    @endpoint("/edit_context_dialogue", ["GET"])
    def edit_context_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which lets the user edit context information.
        """
        
        case_db_proxy = self.create_proxy(case_db)
        context_data = {}
        context_data['general'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_general")
        context_data['organization'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_organization")
        context_data['product'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_product")
        context_data['stakeholders'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_stakeholders")
        context_data['methodandtechnology'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_methodandtechnology")
        context_data['marketandbusiness'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_marketandbusiness")
        
        return render_template("edit_context_dialogue.html", context_data = context_data)     


    @endpoint("/edit_context", ["POST"])
    def edit_context(self, user_id, delegate_token, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the edit_context_dialogue_transition.
        It gets several form parameters: 
        case_id : The ID of the current case
        context_text : The text entered in the main context text area
        It writes the new context information to the database, and then returns a status message to be shown in the main dialogue window.
        """
        # Write the new context information to the database.
        case_db_proxy = self.create_proxy(case_db)
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_general", value = request.values["context_general"])
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_organization", value = request.values["context_organization"])
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_product", value = request.values["context_product"])
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_stakeholders", value = request.values["context_stakeholders"])
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_methodandtechnology", value = request.values["context_methodandtechnology"])
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_marketandbusiness", value = request.values["context_marketandbusiness"])
    
        return "Context information saved."
    
    
if __name__ == '__main__':
    ContextModelService(sys.argv[1]).run()
