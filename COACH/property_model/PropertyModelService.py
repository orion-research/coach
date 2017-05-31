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
# TODO: to suppress
from datetime import datetime
import inspect

def log(*args):
    message = datetime.now().strftime("%H:%M:%S") + " : "
    message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg) + " "
    print(message)
    sys.stdout.flush()
    


class PropertyModelService(coach.Microservice):
    PROPERTY_NOT_ADDED_STRING = ""
    PROPERTY_VALUE_NOT_COMPUTED_STRING = "---"
    ESTIMATION_METHOD_ONTOLOGY_ID_SUFFIX = "_ontology_id"
    PROPERTY_ONTOLOGY_ID_SUFFIX = "_ontology_id"
    
    def __init__(self, settings_file_name = None, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)
        self.orion_ns = "http://www.orion-research.se/ontology#"  # The name space for the ontology used

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
            estimations_methods_names = self._get_estimation_methods(property_name)
            estimation_methods = []
            for estimation_method_name in estimations_methods_names:
                estimation_method_ontology_id = self._get_estimation_method_ontology_id_from_name(estimation_method_name)
                estimated_values = self._get_estimated_value_list(db_infos, alternatives_uri_list, property_name, 
                                                                  estimation_method_ontology_id)
                
                estimation_methods.append({
                                            "estimation_method_name": estimation_method_name,
                                            "estimated_values": estimated_values
                                           })
            
            properties_estimations.append({"property_name": property_name, "estimation_methods": estimation_methods})
 
        log("properties_estimations :", properties_estimations)
        return render_template("properties_overview_dialogue.html", properties_estimations=properties_estimations,
                               alternatives_name_list=alternatives_name_list)
        
    @endpoint("/shortcut_from_overview", ["GET"], "text/html")
    def shortcut_from_overview(self, user_id, user_token, case_db, case_id, alternative_name, property_name, estimation_method_name):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                       {})
    @endpoint("/properties_estimation_methods_dialogue", ["GET"], "text/html")
    def properties_estimation_methods_dialogue_transition(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        return self._properties_estimation_methods_dialogue_transition(db_infos, "", "", "", {})
    
    @endpoint("/manage_estimation_method_form", ["POST"], "text/html")
    def manage_estimation_method_form(self, user_id, user_token, case_db, case_id, alternative_name, property_name, 
                                      estimation_method_name, submit_component):
        PARAMETER_SUFFIX = "_parameter"
        PARAMETER_SUFFIX_LENGTH = len(PARAMETER_SUFFIX)
        PROPERTY_SELECTED_ESTIMATION_METHOD_SUFFIX = "_selected_estimation_method"
        PROPERTY_SELECTED_ESTIMATION_METHOD_SUFFIX_LENGTH = len(PROPERTY_SELECTED_ESTIMATION_METHOD_SUFFIX)
        PROPERTY_VALUE_SUFFIX = "_property_value"
        PROPERTY_VALUE_SUFFIX_LENGTH = len(PROPERTY_VALUE_SUFFIX)
        GOTO_BUTTON_SUFFIX = "_goto_button"
        GOTO_BUTTON_SUFFIX_LENGTH = len(GOTO_BUTTON_SUFFIX)
        
        estimation_method_parameters = {}
        selected_estimation_method_for_used_properties = {}
        used_properties_value = {}
        request_values = request.values.to_dict()
        for key in request_values:
            if key.endswith(PARAMETER_SUFFIX):
                # Remove the trailing suffix in the key
                estimation_method_parameters[key[:-PARAMETER_SUFFIX_LENGTH]] = request_values[key]
            if key.endswith(PROPERTY_SELECTED_ESTIMATION_METHOD_SUFFIX):
                # Remove the trailing suffix in the key
                selected_estimation_method_for_used_properties[key[:-PROPERTY_SELECTED_ESTIMATION_METHOD_SUFFIX_LENGTH]] = request_values[key]
            if key.endswith(PROPERTY_VALUE_SUFFIX):
                # Remove the trailing suffix in the key
                used_properties_value[key[:-PROPERTY_VALUE_SUFFIX_LENGTH]] = request_values[key]

        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        if submit_component == "Add":
            return self._add_property(db_infos, alternative_name, property_name, estimation_method_name,
                                      selected_estimation_method_for_used_properties)
        
        elif submit_component == "Compute":
            return self._handle_compute_button(db_infos, alternative_name, property_name, estimation_method_name, estimation_method_parameters,
                                               selected_estimation_method_for_used_properties, used_properties_value)
            
        elif submit_component == "main_combo_box":
            return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                           selected_estimation_method_for_used_properties)
        elif submit_component.endswith(GOTO_BUTTON_SUFFIX):
            property_name = submit_component[:-GOTO_BUTTON_SUFFIX_LENGTH]
            estimation_method_name = selected_estimation_method_for_used_properties[property_name]
            return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, 
                                                                           estimation_method_name, {})
        else:
            raise MicroserviceException("Unknown submit_component name : '" + submit_component + "'")
        
    def _add_property(self, db_infos, alternative_name, property_name, estimation_method_name, selected_estimation_method_for_used_properties):
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)

        property_ontology_id = self._get_property_ontology_id_from_name(property_name)
        case_db_proxy.add_property(user_id=user_id, user_token=user_token, case_id=case_id, alternative_uri=alternative_uri, 
                                   property_ontology_id=property_ontology_id)
        
        return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                       selected_estimation_method_for_used_properties)
    
    def _handle_compute_button(self, db_infos, alternative_name, property_name, estimation_method_name, estimation_parameters, 
                               selected_estimation_method_for_used_properties, used_properties_value):
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        
        if not self._is_property_linked_to_alternative(db_infos, alternative_name, property_name):
            self._add_property(db_infos, alternative_name, property_name, estimation_method_name, 
                               selected_estimation_method_for_used_properties)
            
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_from_name(estimation_method_name)
        estimation_value = self._compute_estimation_value(estimation_method_ontology_id, estimation_parameters, used_properties_value)
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        
        used_properties_to_estimation_method_ontology_id = {}
        for prop_name in selected_estimation_method_for_used_properties:
            em_name = selected_estimation_method_for_used_properties[prop_name]
            prop_uri = self._get_property_uri_from_name(db_infos, prop_name)
            used_properties_to_estimation_method_ontology_id[prop_uri] = self._get_estimation_method_ontology_id_from_name(em_name)
        
        # Splitting the dictionary in two lists is a workaround to be able to send it with the proxy. However, it
        # does not work when lists are empty 
        estimation_parameters_name = list(estimation_parameters.keys())
        estimation_parameters_value = list(estimation_parameters.values())
        # Another dictionary split
        # TODO: clean up code : empty list can not be passed with the proxy, so we add an element, that we suppressed in the db. 
        used_properties = list(used_properties_to_estimation_method_ontology_id.keys())
        estimation_methods_ontology_id_for_used_properties = list(used_properties_to_estimation_method_ontology_id.values())
        used_properties.append("_")
        estimation_methods_ontology_id_for_used_properties.append("_")
        
        case_db_proxy.add_estimation(user_id=user_id, user_token=user_token, case_id=case_id, alternative_uri=alternative_uri, 
                                     property_uri=property_uri, estimation_method_ontology_id=estimation_method_ontology_id, 
                                     value=estimation_value, estimation_parameters_name=estimation_parameters_name, 
                                     estimation_parameters_value=estimation_parameters_value, used_properties=used_properties,
                                     estimation_methods_ontology_id_for_used_properties=estimation_methods_ontology_id_for_used_properties)
        
        return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                        selected_estimation_method_for_used_properties)
    
        
    def _properties_estimation_methods_dialogue_transition(self, db_infos, selected_alternative_name, selected_property_name, 
                                                           selected_estimation_method_name, selected_estimation_method_for_used_properties):                
        alternatives_name_list = self._get_alternatives(db_infos)[0]
        selected_alternative_name = (selected_alternative_name if selected_alternative_name in 
                                          alternatives_name_list else alternatives_name_list[0])
        
        properties_name_list = self._get_properties_name_list()
        selected_property_name = (selected_property_name if selected_property_name in 
                                       properties_name_list else properties_name_list[0])
        enable_add_button = not self._is_property_linked_to_alternative(db_infos, selected_alternative_name, selected_property_name)

        estimation_methods_name_list = self._get_estimation_methods(selected_property_name)
        selected_estimation_method_name = (selected_estimation_method_name if selected_estimation_method_name in
                                                estimation_methods_name_list else estimation_methods_name_list[0])
        used_properties = self._get_estimation_method_used_properties(db_infos, selected_alternative_name, selected_property_name,
                                                                      selected_estimation_method_name,
                                                                      selected_estimation_method_for_used_properties)
        selected_estimation_method_parameters_list = self._get_selected_estimation_method_parameters(db_infos, selected_alternative_name,
                                                                                                     selected_property_name,
                                                                                                     selected_estimation_method_name)
        
        enable_compute_button = self._is_compute_button_enable(used_properties)
        
        selected_alternative_uri = self._get_alternative_uri_from_name(db_infos, selected_alternative_name)
        estimation_value = self._get_estimation_value(db_infos, selected_alternative_uri, selected_property_name, selected_estimation_method_name)

        return render_template("properties_estimation_methods_dialogue.html", alternatives_name_list=alternatives_name_list,
                               properties_name_list=properties_name_list, estimation_methods_name_list=estimation_methods_name_list,
                               selected_estimation_method_parameters_list=selected_estimation_method_parameters_list, 
                               selected_alternative_name=selected_alternative_name, selected_property_name=selected_property_name,
                               selected_estimation_method_name=selected_estimation_method_name, enable_add_button=enable_add_button,
                               used_properties=used_properties, enable_compute_button=enable_compute_button, estimation_value=estimation_value)

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
            The name (title predicate in the database) of the alternative identified by alternative_uri if alternative_uri
            is an uri of an alternative for this current case, else None.
        ERROR:
            Raise a RuntimeError if more than one alternative with the provided uri is found.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        alternatives_list = case_db_proxy.get_objects(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                      subject=alternative_uri, predicate=orion_ns.title)
        if len(alternatives_list) > 1:
            raise RuntimeError("There should be at most one alternative with the uri " + alternative_uri + " but "
                               + len(alternatives_list) + " were found.")
        return alternatives_list[0] if len(alternatives_list) == 1 else None
     
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
        property_ontology_id = property_name + self.PROPERTY_ONTOLOGY_ID_SUFFIX
        return property_ontology_id
    
    def _get_property_name_from_ontology_id(self, property_ontology_id):
        property_name = property_ontology_id[:-len(self.PROPERTY_ONTOLOGY_ID_SUFFIX)]
        return property_name
    
    def _get_property_uri_from_name(self, db_infos, property_name):
        """
        INPUT:
            property_name: the name of a property
        OUTPUT:
            The uri in the database of the property whom name is property_name, or None if no property in the database match this name.
        ERROR:
            Raise a RuntimeError if more than one property is found in the database with the provided name.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        property_ontology_id = self._get_property_ontology_id_from_name(property_name)
        properties_list = case_db_proxy.get_subjects(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                     predicate=orion_ns.ontology_id, object=property_ontology_id)

        if len(properties_list) > 1:
            raise RuntimeError("There should be at most one property with the name " + property_name + " but "
                               + str(len(properties_list)) + " were found.")
        return properties_list[0] if len(properties_list) == 1 else None

    def _get_estimated_value_list(self, db_infos, alternatives_uri_list, property_name, estimation_method_ontology_id):
        """
        INPUT: 
            alternatives_name_list: a list with the name of all the alternatives.
            property_name: the name of the property on which we want the estimated value.
            estimation_method_ontology_id: the id of the estimation method in the ontology for which the value will be retrieved
        
        OUTPUT:
            A list where each element is a dictionary with three properties: one is the name of the corresponding alternatives, one  
            is the value of the current estimation and the last is a boolean telling whether the value is up-to-date. The keys are 
            respectively "alternative_name", "value" and "up_to_date".
            The value can have 3 different value: 
              - An empty string if the provided property has not be added to the current alternative.
              - The string "---" if the provided property has be added to the current alternative,
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
        
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        result = []
        for alternative_uri in alternatives_uri_list:
            if alternative_uri in linked_alternatives_list_uri:
                db_result = case_db_proxy.get_estimation_value(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                                  alternative_uri=alternative_uri, property_uri=property_uri, 
                                                                  estimation_method_ontology_id=estimation_method_ontology_id)
                if db_result is None:
                    db_result = {"value": self.PROPERTY_VALUE_NOT_COMPUTED_STRING, "up_to_date": True}
            else:
                db_result = {"value": self.PROPERTY_NOT_ADDED_STRING, "up_to_date": True}
            
            alternative_name = self._get_alternative_name_from_uri(db_infos, alternative_uri)
            result.append({"alternative_name": alternative_name, "value": db_result["value"], "up_to_date": db_result["up_to_date"]})
        
        return result
    
    def _is_property_linked_to_alternative(self, db_infos, alternative_name, property_name):
        """
        INPUT:
            alternative_name: the name of the current selected alternative
            property_name: the name of the current selected property
        OUTPUT:
            True if the property is linked to the alternative (has been added to it), False otherwise
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        if property_uri is None:
            return False
        alternatives_uri_list = case_db_proxy.get_objects(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                          subject=property_uri, predicate=orion_ns.belong_to)
        
        return alternative_uri in alternatives_uri_list
    
    def _is_compute_button_enable(self, used_properties):
        for property_ in used_properties:
            try:
                int(property_["value"])
            except ValueError:
                return False
        return True
    
    def _compute_estimation_value(self, estimation_method_ontology_id, estimation_method_parameters, used_properties_name_to_value):
        #TODO: call estimation method
        estimation_value = 1
        for property_name in used_properties_name_to_value:
            estimation_value *= int(used_properties_name_to_value[property_name])
        for (_, parameter_value) in estimation_method_parameters.items():
            estimation_value -= int(parameter_value)
        return estimation_value
    
    def _get_estimation_methods(self, property_name):
        #TODO: fetch estimation methods from database
        if property_name == "Prop 1":
            result = ["E0", "E1", "E2"]
        elif property_name == "Prop 2":
            result = ["E1", "E3"]
        else:
            result = ["E4", "E5", "E6"]
        
        if len(result) == 0:
            raise RuntimeError("At least one estimation method must be available for the property " + property_name)
        return result
    
    def _get_selected_estimation_method_parameters(self, db_infos, alternative_name, property_name, estimation_method_name):
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        #TODO: fetch parameters names from somewhere
        estimation_method_number = int(estimation_method_name[1])
        parameters = string.ascii_lowercase[:estimation_method_number]
        parameters = {x + str(estimation_method_number):0 for x in parameters}
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        if property_uri is None:
            return parameters # if the property has not been added in the database, no parameters could have been stored
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_from_name(estimation_method_name)
        database_parameters = case_db_proxy.get_estimation_parameters(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                                      alternative_uri=alternative_uri, property_uri=property_uri, 
                                                                      estimation_method_ontology_id=estimation_method_ontology_id)
        
        if len(database_parameters) == 0:
            return parameters
             
        # TODO: Check names of the parameters too?
        if len(database_parameters) != len(parameters):
            raise RuntimeError("Parameters stored in the database do not match with those of the estimation method")
        
        return database_parameters
    
    def _get_estimation_method_used_properties(self, db_infos, alternative_name, property_name, estimation_method_name, 
                                               property_to_estimation_method_name_dict):        
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
             
        if estimation_method_name == "E2":
            used_properties_name = ["Prop 2"]
        elif estimation_method_name == "E3":
            used_properties_name = ["Prop 3"]
        elif estimation_method_name == "E6":
            used_properties_name = ["Prop 1", "Prop 2"]
        else:
            used_properties_name = []
            
            
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        if property_uri is not None:
            estimation_method_ontology_id = self._get_estimation_method_ontology_id_from_name(estimation_method_name)
            estimation_uri = case_db_proxy.get_estimation_uri(user_id=user_id, user_token=user_token, case_id=case_id,
                                                              alternative_uri=alternative_uri, property_uri=property_uri,
                                                              estimation_method_ontology_id=estimation_method_ontology_id)
        else:
            estimation_uri = None
        
        if estimation_uri is not None:
            properties_used_to_estimation_method = case_db_proxy.get_estimation_used_properties(user_id=user_id, user_token=user_token,
                                                                                                case_id=case_id, 
                                                                                                estimation_uri=estimation_uri)
        else:
            properties_used_to_estimation_method = {}
        
        result = []
        for current_property_name in used_properties_name:
            
            estimation_method_name_list = self._get_estimation_methods(current_property_name)
            if current_property_name in property_to_estimation_method_name_dict:
                selected_estimation_method_for_current_property = property_to_estimation_method_name_dict[current_property_name]
            else:
                current_property_ontology_id = self._get_property_ontology_id_from_name(current_property_name)
                if current_property_ontology_id in properties_used_to_estimation_method:
                    selected_estimation_method_for_current_property = properties_used_to_estimation_method[current_property_ontology_id]
                    selected_estimation_method_for_current_property = self._get_estimation_method_name_from_ontology_id(selected_estimation_method_for_current_property)
                else:
                    selected_estimation_method_for_current_property = estimation_method_name_list[0]
                
            property_value = self._get_estimation_value(db_infos, alternative_uri, current_property_name,
                                                        selected_estimation_method_for_current_property)
            if property_value is None:
                property_value = self.PROPERTY_VALUE_NOT_COMPUTED_STRING
            
            result.append({"name": current_property_name, "estimation_methods_name": estimation_method_name_list, 
                           "value": property_value["value"], "up_to_date": property_value["up_to_date"],
                           "selected": selected_estimation_method_for_current_property})
        
        log("result :", result)
        return result
    
    def _get_estimation_value(self, db_infos, alternative_uri, property_name, estimation_method_name):
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        if property_uri is None:
            return None
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_from_name(estimation_method_name)
        estimation_value = case_db_proxy.get_estimation_value(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                              alternative_uri=alternative_uri, property_uri=property_uri, 
                                                              estimation_method_ontology_id=estimation_method_ontology_id)
        return estimation_value
        
    def _get_estimation_method_ontology_id_from_name(self, estimation_method_name):
        #TODO: Currently, the estimation_method_ontology_id is the estimation method's name
        estimation_method_ontology_id = estimation_method_name + self.ESTIMATION_METHOD_ONTOLOGY_ID_SUFFIX
        return estimation_method_ontology_id
    
    def _get_estimation_method_name_from_ontology_id(self, estimation_method_ontology_id):
        estimation_method_name = estimation_method_ontology_id[:-len(self.ESTIMATION_METHOD_ONTOLOGY_ID_SUFFIX)]
        return estimation_method_name

if __name__ == '__main__':
    PropertyModelService(sys.argv[1]).run()


















