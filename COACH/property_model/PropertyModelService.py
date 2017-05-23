"""
Created on May 9, 2017

@author: Jan Carlson

The property model service
"""
from curses.ascii import alt
from posix import link
from operator import sub

"""
TODO:



"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))


# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint, MicroserviceException

# Web server framework
from flask.templating import render_template
from flask import request

# Linked data
import rdflib

#TODO: To suppress
import string
from datetime import datetime
import inspect


# TODO: to suppress
def log(*args):
    message = datetime.now().strftime("%H:%M:%S") + " : "
    message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg) + " "
    print(message)
    sys.stdout.flush()
    


class PropertyModelService(coach.Microservice):

    @endpoint("/properties_overview_dialogue", ["GET"], "text/html")
    def properties_dialogue_overview_transition(self, user_id, user_token, case_db, case_id):
        """
        Endpoint which lets the user manage properties.
        """
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        properties_name_list = self._get_properties_name_list()

        # Get all alternatives previously added by the user for the current case
        alternatives_list = self._get_alternatives(db_infos)
        alternatives_name_list = alternatives_list[0]
        alternatives_uri_list = alternatives_list[1]
        properties_estimations = []
        for property_name in properties_name_list:
            # TODO: get estimations methods from the ontology
            estimations_methods_names = self._get_estimation_methods(property_name)
            estimation_methods = [ {
                                        "estimation_method_name": estimation_method_name,
                                        "estimated_values": self._get_estimated_value_list(db_infos, alternatives_uri_list, 
                                                                                           property_name)
                                    } for estimation_method_name in estimations_methods_names]
            
            properties_estimations.append({"property_name": property_name, "estimation_methods": estimation_methods})
 
        return render_template("properties_overview_dialogue.html", properties_estimations=properties_estimations,
                               alternatives_name_list=alternatives_name_list)

    @endpoint("/properties_estimation_methods_dialogue", ["GET"], "text/html")
    def properties_estimation_methods_dialogue_transition(self, user_id, user_token, case_db, case_id):
        return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, "", "", "")
    
    @endpoint("/manage_estimation_method_form", ["POST"], "text/html")
    def manage_estimation_method_form(self, user_id, user_token, case_db, case_id, alternative_name, property_name, 
                                      estimation_method_name, submit_component):
        if submit_component == "Add":
            return self._add_property(user_id, user_token, case_db, case_id, alternative_name, property_name, estimation_method_name)
        elif submit_component == "Compute":
            return self._compute_estimation_method(user_id, user_token, case_db, case_id, alternative_name, property_name, 
                                                   estimation_method_name)
        elif submit_component == "alternative_name":
            return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, alternative_name, 
                                                                           property_name, estimation_method_name)
        elif submit_component == "property_name":
            return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, alternative_name, 
                                                                           property_name, estimation_method_name)
        elif submit_component == "estimation_method_name":
            return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, alternative_name, 
                                                                           property_name, estimation_method_name)
        else:
            raise MicroserviceException("Unknown submit_component name : " + submit_component)
        
    def _add_property(self, user_id, user_token, case_db, case_id, alternative_name, property_name, estimation_method_name):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)

        property_ontology_id = self._get_property_ontology_id_from_name(property_name)
        case_db_proxy.add_property(user_id=user_id, user_token=user_token, case_id=case_id, alternative_uri=alternative_uri, 
                                   property_ontology_id=property_ontology_id)
        
        return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, alternative_name,
                                                                       property_name, estimation_method_name)
    
    def _compute_estimation_method(self, user_id, user_token, case_db, case_id, alternative_name, property_name, estimation_method_name):
        #TODO: add a link between property and alternative if not done yet
        return self._properties_estimation_methods_dialogue_transition(user_id, user_token, case_db, case_id, alternative_name,
                                                                       property_name, estimation_method_name)
    
        
    def _properties_estimation_methods_dialogue_transition(self, user_id, user_token, case_db, case_id, selected_alternative_name,
                                                           selected_property_name, selected_estimation_method_name):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        alternatives_name_list = self._get_alternatives(db_infos)[0]
        selected_alternative_name = (selected_alternative_name if selected_alternative_name in 
                                          alternatives_name_list else alternatives_name_list[0])
        
        properties_name_list = self._get_properties_name_list()
        selected_property_name = (selected_property_name if selected_property_name in 
                                       properties_name_list else properties_name_list[0])
        enable_add_button = self._get_enable_add_button(db_infos, selected_alternative_name, selected_property_name)

        estimation_methods_name_list = self._get_estimation_methods(selected_property_name)
        selected_estimation_method_name = (selected_estimation_method_name if selected_estimation_method_name in
                                                estimation_methods_name_list else estimation_methods_name_list[0])
        selected_estimation_method_parameters_list = self._get_selected_estimation_method_parameters(selected_estimation_method_name)
        
        return render_template("properties_estimation_methods_dialogue.html", alternatives_name_list=alternatives_name_list,
                               properties_name_list=properties_name_list, estimation_methods_name_list=estimation_methods_name_list,
                               selected_estimation_method_parameters_list=selected_estimation_method_parameters_list, 
                               selected_alternative_name = selected_alternative_name, selected_property_name = selected_property_name,
                               selected_estimation_method_name = selected_estimation_method_name, enable_add_button = enable_add_button)

    def _get_alternative_uri_from_name(self, db_infos, alternative_name) :
        """
        INPUT:
            alternative_name: the name (title predicate in the database) of an alternative.
        OUTPUT:
            The first uri for which the identified object is an alternative, with is name being alternative_name.
            If no such uri is found, return None.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id = user_id, token = user_token, case_id = case_id)
        for (alternative_title, alternative_uri) in alternatives_from_db:
            if alternative_title == alternative_name:
                return alternative_uri
        return None

    def _get_alternative_name_from_uri(self, db_infos, alternative_uri):
        """
        INPUT:
            alternative_uri: the uri of an alternative.
        OUTPUT:
            the name (title predicate in the database) of the alternative identified by alternative_uri if alternative_uri
            is an uri of an alternative for this current case, else None.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id = user_id, token = user_token, case_id = case_id)
        for alternative in alternatives_from_db:
            if alternative[1] == alternative_uri:
                return alternative[0]
        return None
    
    def _get_alternatives(self, db_infos):
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id = user_id, token = user_token, case_id = case_id)
        alternatives_name_list = [alternative[0] for alternative in alternatives_from_db]
        alternatives_uri_list = [alternative[1] for alternative in alternatives_from_db]
        return (alternatives_name_list, alternatives_uri_list)
    
    def _get_properties_name_list(self):
        # TODO: Get possible properties from the ontology
        return ["Prop 1", "Prop 2", "Prop 3"]
    
    def _get_property_ontology_id_from_name(self, property_name):
        # TODO: Currently, the property_ontology_id is the property's name
        property_ontology_id = property_name
        return property_ontology_id

    def _get_estimated_value_list(self, db_infos, alternatives_uri_list, property_name):
        """
        INPUT: 
            alternatives_name_list: a list with the name of all the alternatives.
            property_name: the name of the property on which we want the estimated value.
        
        OUTPUT:
            A list where each element is the value of the corresponding alternative (by index).
            The value can have 3 different value: 
              - An empty string if the provided property has not be added to the current alternative.
              - The string "U" if the provided property has be added to the current alternative,
                    but no value has been computed yet.
              - The value which has been computed.
        """
        # TODO: add a fourth possible value, if the value has been computed, but a used property's value has been changed?
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]

        property_ontology_id = self._get_property_ontology_id_from_name(property_name)        
        linked_alternatives_list_uri = case_db_proxy.get_alternative_from_property_ontology_id(user_id=user_id, user_token=user_token, 
                                                                                               case_id=case_id, 
                                                                                               property_ontology_id=property_ontology_id)

        linked_alternatives_list = []
        for alternative_uri in linked_alternatives_list_uri:
            linked_alternatives_list.append(self._get_alternative_name_from_uri(db_infos, alternative_uri))

        result = []
        for alternative_uri in alternatives_uri_list:
            alternative_name = self._get_alternative_name_from_uri(db_infos, alternative_uri)
            result.append("U" if alternative_name in linked_alternatives_list else "")
        
        return result
    
    def _get_enable_add_button(self, db_infos, alternative_name, property_name):
        """
        INPUT:
            alternative_name: the name of the current selected alternative
            property_name: the name of the current selected property
        OUTPUT:
            True if the add button should be enable, otherwise False. The add button should be enable iff 
            there is no link between the current alternative and property. In other words, return True if
            a link exists, otherwise False
        """
        return self._get_estimated_value_list(db_infos, [self._get_alternative_uri_from_name(db_infos, alternative_name)], 
                                              property_name)[0] == ""
    
    def _get_estimation_methods(self, selected_property_name):
        #TODO: fetch estimation methods from database
        if selected_property_name == "Prop 1":
            return ["E1", "E2"]
        elif selected_property_name == "Prop 2":
            return ["E1", "E3"]
        else:
            return ["E4", "E5", "E6"]
    
    def _get_selected_estimation_method_parameters(self, estimation_method_name):
        #TODO: fetch parameters from somewhere
        estimation_method_number = int(estimation_method_name[1])
        parameters = string.ascii_lowercase[:estimation_method_number]
        parameters = [x + str(estimation_method_number) for x in parameters]
        return parameters


if __name__ == '__main__':
    PropertyModelService(sys.argv[1]).run()


















