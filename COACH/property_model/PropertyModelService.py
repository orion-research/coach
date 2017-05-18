"""
Created on May 9, 2017

@author: Jan Carlson

The property model service
"""
from curses.ascii import alt

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

# Linked data
import rdflib


class PropertyModelService(coach.Microservice):
    def __init__(self, settings_file_name=None, working_directory=None):
        super().__init__(settings_file_name, working_directory=working_directory)
        self.orion_ns = "http://www.orion-research.se/ontology#"


    @endpoint("/properties_dialogue", ["GET"], "text/html")
    def properties_dialogue_transition(self, user_id, user_token, case_db, case_id):
        """
        Endpoint which lets the user manage properties.
        """

        case_db_proxy = self.create_proxy(case_db)

        # Get all alternatives previously added by the user for the current case
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id=user_id, token=user_token, case_id=case_id)
        alternatives = []
        for (alternative_title, alternative_uri) in alternatives_from_db:
            properties_list = case_db_proxy.get_object_properties(user_id=user_id, user_token=user_token, case_id=case_id,
                                                                  resource=alternative_uri, property_name="has")
            properties_list = [property_.replace("%20", " ") for property_ in properties_list]
            alternatives.append({"title": alternative_title, "properties":properties_list})

        # TODO: Get possible properties from the ontology
        properties = ["Prop 1", "Prop 2", "Prop 3"]

        # TODO: Check if possible properties match with properties in alternative?

        # TODO: update alternatives to that format:
        # [{name: "Alt 1", selected_properties:["Prop 1"], selectable_properties:["Prop 2", "Prop 3"]}
        # So only selectable properties are displayed for each alternative ?

        return render_template("properties_dialogue.html", alternatives=alternatives, properties=properties)

    @endpoint("/add_property", ["POST"], "text/html")
    def add_property(self, user_id, user_token, case_db, case_id, alternative, property_):
        case_db_proxy = self.create_proxy(case_db)
        alternative_uri = self.get_alternative_uri(user_id, user_token, case_id, alternative, case_db_proxy)
        property_uri = property_.replace(' ', '%20')
        case_db_proxy.add_object_property(user_id=user_id, user_token=user_token, case_id=case_id, resource1=alternative_uri,
                                                property_name="has", resource2=property_uri)
        return self.properties_dialogue_transition(user_id, user_token, case_db, case_id)

    def get_alternative_uri(self, user_id, user_token, case_id, alternative_title, case_db_proxy) :
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id=user_id, token=user_token, case_id=case_id)
        for (alternative_title, alternative_uri) in alternatives_from_db:
            if alternative_title == alternative_title:
                return alternative_uri
        return None
    
if __name__ == '__main__':
    PropertyModelService(sys.argv[1]).run()


















