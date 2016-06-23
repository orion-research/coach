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

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class ContextModelService(coach.Microservice):
# JC: Or should this be one specialization of a common ContextModel Service class defined in coach.py??? 



    def create_endpoints(self):

        self.ms.logger.info("Creating endpoints!")
        
        # States, represented by dialogues
        self.edit_context_dialogue = self.create_state("edit_context_dialogue.html")
        
        
        # Endpoints for transitions between the states without side effects
        self.ms.add_url_rule("/edit_context_dialogue", view_func = self.edit_context_dialogue_transition)
        
        # Endpoints for transitions between states with side effects
        self.ms.add_url_rule("/edit_context", view_func = self.edit_context, methods = ["POST"])




    def edit_context_dialogue_transition(self):
        """
        Endpoint which lets the user edit context information.
        """
        self.ms.logger.info("Entering edit_context_dialogue_transition 1");
        
#        root = request.values["root"]
#        case_id = request.values["case_id"]
        self.ms.logger.info("Entering edit_context_dialogue_transition 2");

#        tst = self.go_to_state(self.edit_context_dialogue, this_process = request.url_root, 
#                                root = root, case_id = case_id)
        
        self.ms.logger.info("Entering edit_context_dialogue_transition 3");
#        return "Test"
        return self.go_to_state(self.edit_context_dialogue, this_process = "this", 
                                root = "root", case_id = "case_id")     
        #return self.go_to_state(self.edit_context_dialogue, this_process = request.url_root, 
        #                        root = root, case_id = case_id)
        



    def edit_context(self):
        # To be done!
        return "To be done"


    
if __name__ == '__main__':
    ContextModelService(sys.argv[1]).run()
