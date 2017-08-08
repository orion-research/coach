"""
Created on May 9, 2017

@author: Jan Carlson

The property model service
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

import requests

# Linked data
import rdflib

# TODO: to suppress
from datetime import datetime
import inspect

def log(*args, verbose = True):
    message = "" if verbose else "::"
    if verbose:
        message = datetime.now().strftime("%H:%M:%S") + " : "
        message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg).replace("\n", "\n::") + " "
    print(message)
    sys.stdout.flush()


class PropertyModelService(coach.Microservice):
    """
    This class handle all the logic to interact with properties, from linked a property to an alternative to compute
    an estimation of this property with an predefined estimation method. 
    In all this class, user_id, user_token, case_db and case_id are identifier used by the database. In some methods, they are
    packed in a dicitionary called "db_infos".
    """
    PROPERTY_NOT_ADDED_STRING = ""
    PROPERTY_VALUE_NOT_COMPUTED_STRING = "---"
    
    def __init__(self, settings_file_name = None, working_directory = None, *args, **kwargs):
        super().__init__(settings_file_name, working_directory = working_directory, *args, **kwargs)
        self.orion_ns = "http://www.orion-research.se/ontology#"  # The name space for the ontology used
        self.ontology = None

    @endpoint("/properties_overview_dialogue", ["GET"], "text/html")
    def properties_dialogue_overview_transition(self, user_id, user_token, case_db, case_id):
        """
        DESCRIPTION:
            Endpoint which gives to the user an overview of the alternatives' current state. It creates an array, with the x-axis
            as the alternatives, and the y-axis as the properties. Moreover, each row of property is subdivided according to the 
            different estimation methods available for this property. Each cell of the array can contain three different value:
            an empty string if the property has not been added to the alternative, '---' if the property has been added, but no
            estimation has been done with this estimation method, or the value of the estimation.
            Finally, each cell of the array is a link to manage the defined alternative, property and estimation method
        OUTPUT:
            The overview view.
        """
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        properties_name_list = self._get_properties_name_list(db_infos)

        # Get all alternatives previously added by the user for the current case
        alternatives_list = self._get_alternatives(db_infos)
        alternatives_name_list = alternatives_list[0]
        alternatives_uri_list = alternatives_list[1]
        properties_estimations = []
        for property_name in properties_name_list:
            estimations_methods_names = self._get_estimation_methods_name(property_name)
            estimation_methods = []
            for estimation_method_name in estimations_methods_names:
                estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
                estimated_values = self._get_estimated_value_list(db_infos, alternatives_uri_list, property_name, 
                                                                  estimation_method_ontology_id)
                
                estimation_methods.append({
                                            "estimation_method_name": estimation_method_name,
                                            "estimated_values": estimated_values
                                           })
            
            properties_estimations.append({"property_name": property_name, "estimation_methods": estimation_methods})
 
        return render_template("properties_overview_dialogue.html", properties_estimations=properties_estimations,
                               alternatives_name_list=alternatives_name_list)
        
    @endpoint("/shortcut_from_overview", ["GET"], "text/html")
    def shortcut_from_overview(self, user_id, user_token, case_db, case_id, alternative_name, property_name, estimation_method_name):
        """
        DESCRIPTION:
            This endpoint redirect to the estimation method's view, with the provided alternative, property and estimation method selected.
        INPUT:
            alternative_name: the name of the default selected alternative in the estimation method view.
            property_name: the name of the default selected property in the estimation method view.
            estimation_method_name: the name of the default selected estimation method in the estimation method view.
        OUTPUT:
            The estimation method view.
        """
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        
        return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                       {})
    @endpoint("/properties_estimation_methods_dialogue", ["GET"], "text/html")
    def properties_estimation_methods_dialogue_transition(self, user_id, user_token, case_db, case_id):
        """
        DESCRIPTION:
            This endpoint display the estimation method's view, with default selection for alternatives, properties and estimation methods.
            If there is no alternative, an error message is displayed, inviting the user to add some.
        OUTPUT:
            The estimation method view.
        """
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        alternatives_uri_list = self._get_alternatives(db_infos)[1]
        if len(alternatives_uri_list) == 0:
            return "Add alternatives before going to this page"
        return self._properties_estimation_methods_dialogue_transition(db_infos, "", "", "", {})
    
    @endpoint("/manage_estimation_method_form", ["POST"], "text/html")
    def manage_estimation_method_form(self, user_id, user_token, case_db, case_id, alternative_name, property_name, 
                                      estimation_method_name, submit_component):
        """
        DESCRIPTION:
            This methods is used to choose an action depending of submit_component, and returned the estimation method view.
        INPUT:
            alternative_name: the name of the alternative to be selected in the estimation_method_view.
            property_name: the name of the property to be selected in the estimation method view.
            estimation_method_name: the name of the estimation method to be selected in the estimation method view.
            submit_component: this parameter is used to determined which action need to be done. The different possible value are:
                 - "Compute": it will call the provided estimation method, and stores the resulting value in the database for
                        the provided alternative and property. For the computation, it can use parameters and dependents properties. This 
                        parameters and dependents properties are provided in the http request.
                 - "Delete": it will delete the estimation defined by the triplet (alternative, property, estimation method) from the
                        database. The value of this estimation as well as all the stored parameters will be deleted. Moreover, all the
                        dependents properties will be tagged "out_of_date".
                 - "main_combo_box": it will refresh the estimation method view. Options in the main combo box can change, as well as
                        the parameters list and the dependents properties list. The default value of each parameter is got from the 
                        database if any, else 0.
                 - "<property_name>_goto_button": it will refresh the estimation method view. The selected alternative will be 
                        alternative_name. However, submit_component must be in the form <property_name>_goto_button, and the selected
                        property is defined by the first part of submit_component's name. Finally, the selected estimation_method is
                        got from the request, from the value of the parameter <property_name>_selected_estimation_method.
            Besides those named parameters, the request can contain several optional parameters, which are defined by their suffix:
                 - "<parameter_name>_parameter": The first part defined an estimation method's parameter's name. The value is 
                        the value of the estimation method's parameter.
                 - "<property_name>_property_value": the first part defined the name of the dependent property. The value of this 
                        dependent property is the value of the http parameter.
                 - "<property_name>_selected_estimation_method": this parameter describes the name of the estimation
                        method selected for the dependent property.
        OUTPUT:
            The estimation method view.
        ERROR:
            Raise a MicroserviceException if submit_component is not among those describe above.
        """
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
        
        if submit_component == "Compute":
            self._handle_compute_button(db_infos, alternative_name, property_name, estimation_method_name, estimation_method_parameters,
                                        selected_estimation_method_for_used_properties, used_properties_value)
        elif submit_component == "Delete":
            self._handle_delete_button(db_infos, alternative_name, property_name, estimation_method_name)
        elif submit_component == "main_combo_box":
            pass # Avoid the Exception to be raised.
        elif submit_component.endswith(GOTO_BUTTON_SUFFIX):
            property_name = submit_component[:-GOTO_BUTTON_SUFFIX_LENGTH]
            estimation_method_name = selected_estimation_method_for_used_properties[property_name]
            selected_estimation_method_for_used_properties = {}
        else:
            raise RuntimeError("Unknown submit_component name : '" + submit_component + "'")
        
        return self._properties_estimation_methods_dialogue_transition(db_infos, alternative_name, property_name, estimation_method_name,
                                                                       selected_estimation_method_for_used_properties)
        
    def _add_property(self, db_infos, alternative_name, property_name):
        """
        DESCRIPTION:
            Store in the database the fact that the provided property is added to the provided alternative.
        INPUT:
            alternative_name: Defined the alternative which will be linked to the property.
            property_name: Defined the property which will be linked to the alternative. 
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)

        property_ontology_id = self._get_property_ontology_id_name(property_name)
        case_db_proxy.add_property(user_id=user_id, user_token=user_token, case_id=case_id, alternative_uri=alternative_uri, 
                                   property_ontology_id=property_ontology_id)
    
    def _handle_compute_button(self, db_infos, alternative_name, property_name, estimation_method_name, estimation_parameters, 
                               selected_estimation_method_for_used_properties, used_properties_value):
        """
        DESRCIPTION:
            Compute an estimation using the provided estimation method, parameters and dependents properties. If the property has not 
            been added to the alternative, add it. Store the value of the estimation as well as those of the parameters in the database.
        INPUT:
            alternative_name: The name of the alternative for which the estimation is computed.
            property_name: The name of the property for which the estimation is computed.
            estimation_method_name: The name of the estimation method used to compute the estimation.
            estimation_parameters: A dictionary, containing all the parameters used by the provided estimation method. Each key is the name
                of a parameter, with the corresponding value the value of this parameter.
            selected_estimation_method_for_used_properties: A dictionary, containing the dependents properties of the provided estimation
                method as keys, and the estimation method used for this dependent property as values.
            used_properties_value: A dictionary, containing the dependents properties as keys, and their value as values.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        
        if not self._is_property_linked_to_alternative(db_infos, alternative_name, property_name):
            self._add_property(db_infos, alternative_name, property_name)
        
        estimation_value = self._compute_estimation_value(estimation_method_name, estimation_parameters, used_properties_value)
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        
        used_properties_to_estimation_method_ontology_id = {}
        for prop_name in selected_estimation_method_for_used_properties:
            em_name = selected_estimation_method_for_used_properties[prop_name]
            prop_uri = self._get_property_uri_from_name(db_infos, prop_name)
            used_properties_to_estimation_method_ontology_id[prop_uri] = self._get_estimation_method_ontology_id_name(em_name)

        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        case_db_proxy.add_estimation(user_id=user_id, user_token=user_token, case_id=case_id, alternative_uri=alternative_uri, 
                                     property_uri=property_uri, estimation_method_ontology_id=estimation_method_ontology_id, 
                                     value=estimation_value, estimation_parameters=estimation_parameters, 
                                     used_properties_to_estimation_method_ontology_id=used_properties_to_estimation_method_ontology_id)
        
    
    def _handle_delete_button(self, db_infos, alternative_name, property_name, estimation_method_name):
        """
        DESCRIPTION:
            Delete the provided estimation, defined by the triplet (alternative, property, estimation method) from the database,
            as well as all its parameters. All estimation that depends of this one are tagged "out_of_date".
        INPUT:
            alternative_name: The alternative's name of the triplet defining the estimation.
            property_name: The property's name of the triplet defining the estimation.
            estimation_method_name: The estimation method's name of the triplet defining the estimation.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        case_db_proxy.remove_estimation(user_id=user_id, user_token=user_token, case_id=case_id,
                                                          alternative_uri=alternative_uri, property_uri=property_uri,
                                                          estimation_method_ontology_id=estimation_method_ontology_id)
        
                
    def _properties_estimation_methods_dialogue_transition(self, db_infos, selected_alternative_name, selected_property_name, 
                                                           selected_estimation_method_name, selected_estimation_method_for_used_properties):
        """
        DESCRIPTION:
            This method displays the estimation method view.
        INPUT:
            selected_alternative_name: The name of the alternative that will be selected in the estimation method view. If the provided
                name does not match any in the alternatives' list, the first alternative of the list will be selected.
            selected_property_name: The name of the property that will be selected in the estimation method view. If the provided name
                does not match any in the properties' list, the first property of the list will be selected.
            selected_estimation_method_name: The name of the estimation method that will be selected in the estimation method view. If the
                provided name does not match any in the estimation methods' list, the first estimation method of the list will be selected.
            selected_estimation_method_for_used_properties: A dictionary, containing the name of the dependents properties as keys, and the
                name of the estimation method that will be selected as value. If, for a given dependent property, their is no such key in
                the dictionary, or the value is not in the list of available estimation methods for this property, the first estimation
                method available for this property will be selected. If there is a key which is not a dependent property's name, it is
                ignored.
        OUTPUT:
            The estimation method view. It contains three combo box (alternative, property, estimation method), then a list of dependents
            properties for the selected estimation method, and then a list of parameters for the selected estimation method. Finally, a 
            compute button is present at the bottom of the page.
        """
        alternatives_name_list = self._get_alternatives(db_infos)[0]
        selected_alternative_name = (selected_alternative_name if selected_alternative_name in 
                                     alternatives_name_list else alternatives_name_list[0])
        
        properties_name_list = self._get_properties_name_list(db_infos)
        selected_property_name = (selected_property_name if selected_property_name in 
                                       properties_name_list else properties_name_list[0])

        estimation_methods_name_list = self._get_estimation_methods_name(selected_property_name)
        selected_estimation_method_name = (selected_estimation_method_name if selected_estimation_method_name in
                                                estimation_methods_name_list else estimation_methods_name_list[0])
        
        used_properties = self._get_estimation_method_used_properties(db_infos, selected_alternative_name, selected_property_name,
                                                                      selected_estimation_method_name,
                                                                      selected_estimation_method_for_used_properties)

        selected_estimation_method_parameters_list = self._get_estimation_method_parameters(db_infos, selected_alternative_name,
                                                                                             selected_property_name,
                                                                                             selected_estimation_method_name)
        
        enable_compute_button = self._is_compute_button_enable(used_properties)
        enable_delete_button = self._is_delete_button_enable(db_infos, selected_alternative_name, selected_property_name,
                                                             selected_estimation_method_name)
        
        selected_alternative_uri = self._get_alternative_uri_from_name(db_infos, selected_alternative_name)
        estimation_value = self._get_estimation_value(db_infos, selected_alternative_uri, selected_property_name, selected_estimation_method_name)

        return render_template("properties_estimation_methods_dialogue.html", alternatives_name_list=alternatives_name_list,
                               properties_name_list=properties_name_list, estimation_methods_name_list=estimation_methods_name_list,
                               selected_estimation_method_parameters_list=selected_estimation_method_parameters_list, 
                               selected_alternative_name=selected_alternative_name, selected_property_name=selected_property_name,
                               selected_estimation_method_name=selected_estimation_method_name, used_properties=used_properties, 
                               enable_compute_button=enable_compute_button, enable_delete_button=enable_delete_button,
                               estimation_value=estimation_value)

    def _get_alternative_uri_from_name(self, db_infos, alternative_name) :
        """
        DESCRIPTION:
            Returns the database uri of an alternative defined by its name.
        INPUT:
            alternative_name: The name (title predicate in the database) of an alternative.
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
        DESCRIPTION:
            Returns the name of an alternative defined by its database uri.
        INPUT:
            alternative_uri: The uri of an alternative.
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
        """
        DESCRIPTION:
            Returns two lists of alternatives from the database, one a list of name, the other a list of uri.
        OUTPUT:
            A tuple containing two lists of alternatives from the database, one a list of name, the other a list of uri.
            The first element of the tuple is the list of name, the second one is the list of uri. 
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternatives_from_db = case_db_proxy.get_decision_alternatives(user_id = user_id, token = user_token, case_id = case_id)
        alternatives_name_list = [alternative[0] for alternative in alternatives_from_db]
        alternatives_uri_list = [alternative[1] for alternative in alternatives_from_db]
        return (alternatives_name_list, alternatives_uri_list)
    
    def _get_properties_name_list(self, db_infos):
        """
        DESCRIPTION:
            Returns a list containing the name of all properties from the ontology, sorted by name.
        OUTPUT:
            A list containing the name of all properties from the ontology, sorted by name.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        result = [prop_tuple[2].toPython() for prop_tuple in self._get_ontology_instances(orion_ns.Property, db_infos)]
        result.sort()
        return result
    
    def _get_ontology(self, db_infos = None):
        """
        DESCRIPTION:
            Returns the ontology stored in the database. The query to the database is done only once and the result is stored. 
            Thanks to that, the following times, the stored object can be returned immediately.
        INPUT:
            db_infos: db_infos is a dictionary, which contains a key "case_db_proxy", which is the proxy to access database. 
            It can be omitted if the ontology has already been got from the database.
        OUTPUT:
            The ontology stored in the database. 
        ERROR:
            Throw a TypeError if db_infos is omitted or does not contains a key "case_db_proxy" whereas the ontology has not yet
            been got from the database.
        """
        if not self.ontology:
            case_db_proxy = db_infos["case_db_proxy"]
            self.ontology = rdflib.ConjunctiveGraph()
            self.ontology.parse(data = case_db_proxy.get_ontology(format_ = "ttl"), format = "ttl")
        return self.ontology
    
    def _get_ontology_instances(self, class_name, db_infos = None):
        """
        DESCRIPTION:
            Returns a list containing all the instances of the given class in the ontology.
        INPUT:
            The name of a class in the ontology. It is the complete uri including the prefix.
        OUTPUT:
            A list of tuples, where the tuple elements are the instances' uri, gradeID, title, and description
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        q = """\
        SELECT ?instance_ontology_uri ?grade_id ?title ?description
        WHERE {
            ?instance_ontology_uri a ?class_name .
            ?instance_ontology_uri orion:gradeId ?grade_id .
            ?instance_ontology_uri orion:title ?title .
            ?instance_ontology_uri orion:description ?description .
        }
        """
        result = self._get_ontology(db_infos).query(q, initNs = { "orion": orion_ns }, 
                                                    initBindings = { "?class_name": class_name })
        return list(result)
    
    def _get_property_ontology_id_name(self, property_attribute, is_property_attribute_name = True):
        """
        DESCRIPTION:
            Returns the name or the ontology id of the property defined by property_attribute.
        INPUT:
            property_attribute: The name or the ontology id of a property.
            is_property_attribute_name: A boolean, which should be True if property_attribute is the name of a property,
                and False if property_attribute is the ontology_id of the property.
        OUTPUT:
            If is_property_attribute is True, returns the ontology id of the property defined by the name property_attribute.
            Otherwise, returns the name of the property defined by the ontology id property_attribute.
        ERROR:
            Raise a RuntimeError if no match were found with property_attribute.
        """
        if is_property_attribute_name:
            index_returned = 0
            index_look_for = 2
        else:
            index_returned = 2
            index_look_for = 0
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        # Here we can omit db_infos because _get_ontology has already been called to get the properties' name
        properties_list = self._get_ontology_instances(orion_ns.Property)
        for property_tuple in properties_list:
            if property_tuple[index_look_for].toPython() == property_attribute:
                return property_tuple[index_returned].toPython()
        raise RuntimeError("The provided property attribute " + property_attribute + " should be in the ontology")
    
    def _get_property_uri_from_name(self, db_infos, property_name):
        """
        DESCRIPTION:
            Returns the uri in the database of a property identified by the name property_name.
        INPUT:
            property_name: The name of a property.
        OUTPUT:
            The uri in the database of the property whom name is property_name, or None if no property in the database match this name.
        ERROR:
            Raise a RuntimeError if more than one property is found in the database with the provided name.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        property_ontology_id = self._get_property_ontology_id_name(property_name)
        return case_db_proxy.get_property_uri_from_ontology_id(user_id=user_id, token=user_token, case_id=case_id, 
                                                               property_ontology_id=property_ontology_id)
    
    def _get_property_type(self, property_name):
        """
        DESCRIPTION:
            Return the type of the property defined by property_name.
        INPUT:
            property_name: The name of a property.
        OUTPUT:
            The type of the property defined by property_name.
        ERROR:
            Raise a RuntimeError if there is no type or more than one type for the provided property, or if the type 
            is invalid. Valid types are "text", "float" and "integer".
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        query = """ SELECT ?property_type
                    WHERE {
                        ?property_ontology_uri a orion:Property .
                        ?property_ontology_uri orion:title ?property_name .
                        ?property_ontology_uri orion:type ?property_type .
                    }
        """
        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns}, 
                                                  initBindings = {"property_name": rdflib.Literal(property_name)})
        result = [t.toPython() for (t,) in query_result]
        if len(result) != 1:
            raise RuntimeError("The property " + property_name + " must have exactly 1 type, but " + str(len(result)) + " were found.")
        
        allowed_types = ["text", "float", "integer"]
        if result[0] not in allowed_types:
            raise RuntimeError("The property " + property_name + " have an unknown type (" + result[0] + "). Valid types are: "
                               + ", ".join(allowed_types) + ".")
        return result[0]

    def _get_estimated_value_list(self, db_infos, alternatives_uri_list, property_name, estimation_method_ontology_id):
        """
        DESCRIPTION:
            Returns a list with the value of a given estimation method and property for all alternatives in alternatives_uri_list.
        INPUT: 
            alternatives_uri_list: A list with the uri of all the alternatives for which we want the value of the estimation.
            property_name: The name of the property on which we want the estimated value.
            estimation_method_ontology_id: The id of the estimation method in the ontology for which the value will be retrieved
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
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]

        property_ontology_id = self._get_property_ontology_id_name(property_name)        
        linked_alternatives_list_uri = case_db_proxy.get_alternative_from_property_ontology_id(user_id=user_id, token=user_token, 
                                                                                               case_id=case_id, 
                                                                                               property_ontology_id=property_ontology_id)
        
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        result = []
        for alternative_uri in alternatives_uri_list:
            if alternative_uri in linked_alternatives_list_uri:
                db_result = case_db_proxy.get_estimation_value(user_id=user_id, token=user_token, case_id=case_id, 
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
        DESCRIPTION:
            Returns True if the provided property has been added to the provided alternative, False otherwise.
        INPUT:
            alternative_name: The name of an alternative.
            property_name: The name of a property.
        OUTPUT:
            True if the property is linked to the alternative (has been added to it), False otherwise.
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
        """
        DESCRIPTION:
            Return true if the compute button is enable, otherwise False.
        INPUT:
            used_properties: A list, in which each element is a dictionary containing the key computed.
        OUTPUT:
            True if, for each element of the list, the estimation has been computed, otherwise False.
        """
        for property_ in used_properties:
            if not property_["computed"]:
                return False
        return True
    
    def _is_delete_button_enable(self, db_infos, alternative_name, property_name, estimation_method_name):
        """
        DESCRIPTION:
            Return True if the delete button is enable, otherwise false.
            The delete button is enable if the current estimation has already been added to the database.
            The current estimation is defined by the triplet (alternative, property, estimation_method).
        INPUT:
            alternative_name: The alternative's name of the triplet defining the estimation.
            property_namt: The property's name of the triplet defining the estimation.
            estimation_method_name: The estimation method's name of the estimation method defining the estimation.
        OUTPUT:
            True if the provided estimation has already been added in the database, false otherwise.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        
        estimation_method_uri = case_db_proxy.get_estimation_uri(user_id=user_id, token=user_token, case_id=case_id,
                                                                 alternative_uri=alternative_uri, property_uri=property_uri,
                                                                 estimation_method_ontology_id=estimation_method_ontology_id)
        return (estimation_method_uri is not None)
    
    def _compute_estimation_value(self, estimation_method_name, estimation_method_parameters, used_properties_name_to_value):
        """
        DESCRIPTION:
            Calls the provided estimation method to compute the estimation, and returns the result. 
        INPUT:
            estimation_method_name: The name of the estimation method used to do the computation.
            estimation_method_parameters: A dictionary, containing the parameters' name as keys, and their value as value.
            used_properties_name_to_value: A dictionary, containing the name of the dependents properties as keys, and their value as value.
        OUTPUT:
            The estimation computed by the estimation method.
        """
        estimation_method_microservice_name = self._get_estimation_method_microservice_name(estimation_method_name)
        estimation_method_service = self.get_setting(estimation_method_microservice_name)
        global_settings = self.get_setting("object")
        estimation_method_service_address = (global_settings["protocol"] + "://" + global_settings["host"] + ":" 
                                            + str(estimation_method_service["port"]))
        
        estimation_method_proxy = self.create_proxy(estimation_method_service_address)
        return estimation_method_proxy.compute(parameters_dict=estimation_method_parameters, properties_dict=used_properties_name_to_value)
        
    def _get_estimation_method_microservice_name(self, estimation_method_name):
        """
        DESCRIPTION:
            Return the name of the microservice used by the provided estimation method.
        INTPUT:
            estimation_method_name: The name of an estimation method.
        OUTPUT:
            The name of the microservice used by the provided estimation method.
        ERROR:
            Raise a RuntimeError if no microservice name is found, or if more than 1 are found.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        query = """ SELECT ?estimation_method_microservice_name
                    WHERE {
                        ?estimation_method_ontology_uri a orion:EstimationMethod .
                        ?estimation_method_ontology_uri orion:title ?estimation_method_name .
                        ?estimation_method_ontology_uri orion:microserviceName ?estimation_method_microservice_name .
                    }
        """
        
        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns},
                                                  initBindings = {"estimation_method_name": rdflib.Literal(estimation_method_name)})
        result = [e.toPython() for (e,) in query_result]
        if len(result) != 1:
            raise RuntimeError("There should be exactly one microservice name for the estimation method " + estimation_method_name 
                               + " but " + str(len(result)) + " were found.")
        return result[0]
    
    def _get_estimation_methods_name(self, property_name):
        """
        DESCRIPTION:
            Returns a list with the name of all estimation methods in the ontology which are available for the provided property.
        INPUT:
            property_name: The name of the property for which the returned estimation methods are available.
        OUTPUT:
            A list with the name of all estimation methods available for the provided property.
            The estimation method "ExpertEstimate" is a default to all properties, and it is declined in 3 different estimation methods,
            depending of the type of the property.
        """
        property_ontology_id = self._get_property_ontology_id_name(property_name)
        orion_ns = rdflib.Namespace(self.orion_ns)
        query = """ SELECT ?estimation_method_name
                    WHERE {
                        ?estimation_method_ontology_uri a orion:EstimationMethod .
                        ?estimation_method_ontology_uri orion:belongTo ?property_ontology_uri .
                        ?estimation_method_ontology_uri orion:type ?type .
                        ?property_ontology_uri orion:type ?type .
                        ?estimation_method_ontology_uri orion:title ?estimation_method_name .
                    }
        """
        
        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns}, 
                                                  initBindings = {"property_ontology_uri": rdflib.URIRef(property_ontology_id)})
        
        result = [e.toPython() for (e,) in query_result]
        property_type = self._get_property_type(property_name)
        if property_type == "text":
            result.append("Expert estimate text")
        elif property_type == "float":
            result.append("Expert estimate float")
        else:
            result.append("Expert estimate integer")
            
        return result
    
    def _get_estimation_method_parameters(self, db_infos, alternative_name, property_name, estimation_method_name):
        """
        DESCRIPTION:
            Return the list of parameters used by the provided estimation method (see documentation of 
            _get_estimation_method_parameters_from_ontology to the detailed structure of the list).
            An estimation is defined by a triplet (alternative, property, estimation method).
        INTPUT:
            alternative_name: The name of the alternative in the triplet.
            property_name: The name of the property in the triplet.
            estimation_method_ontology_id: The ontology id of the estimation method in the triplet.
        OUTPUT:
            The list of parameters used by the provided estimation method (see documentation of 
            _get_estimation_method_parameters_from_ontology to the detailed structure of the list).
            The value of each parameter is the value it has for the last computation of the provided estimation.
            If no estimation has been computed yet, its value is the default value from the ontology.
        ERROR:
            Raise a RuntimeError if there is parameters in the database, but their number or their name is different from the number of
            parameters used by the estimation method.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        ontology_parameters = self._get_estimation_method_parameters_from_ontology(estimation_method_name)
        
        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        if property_uri is None:
            # if the property has not been added in the database, no estimation could have been computed, 
            # so no parameters could have been stored in the database.
            return ontology_parameters
        
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        database_parameters = case_db_proxy.get_estimation_parameters(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                                      alternative_uri=alternative_uri, property_uri=property_uri, 
                                                                      estimation_method_ontology_id=estimation_method_ontology_id)
        
        if len(database_parameters) == 0:
            return ontology_parameters
        
        number_of_ontology_parameters = sum([len(category["parameters"]) for category in ontology_parameters])
        if len(database_parameters) != number_of_ontology_parameters:
            raise RuntimeError("Parameters stored in the database do not match with those of the estimation method.")
        
        for parameter_category in ontology_parameters:
            for parameter in parameter_category["parameters"]:
                try:
                    parameter["value"] = database_parameters[parameter["name"]]
                except KeyError as e:
                    raise KeyError("Parameter " + parameter["value"] + " is not stored in the database.") from e
            
        return ontology_parameters
    
    def _get_estimation_method_parameters_from_ontology(self, estimation_method_name):
        """
        DESCRIPTION:
            Return a list in which each element is a dictionary representing a category of parameters. Each category contains
            a key "category_name" with the name of the category, and a key "parameters", with the list of the parameters used by 
            the provided estimation method for this category. The first category's name is always None. It is the only category
            which can have an empty list of parameters. Consequently, if there is no parameters, the returned list is:
            [{"category_name": None, "parameters":[]}]
        INPUT:
            estimation_method_name: The name of the estimation method for which the parameters are retrieved.
        OUTPUT:
            A list in which each element is a dictionary representing a category. Each category is:
            {
                "category_name": <category_name>,
                "parameters": <parameter_list>
            }
            The name of the first category is always None (parameters without a category). It is the only category which can have
            an empty list of parameters.
            <parameter_list> is a list in which each element is a dictionary representing a parameter used by the provided 
            estimation method.
            Each dictionary is: {
                                    "name": <parameter_name>, 
                                    "type": <parameter_type>,
                                    "value": <parameter_default_value>,
                                    ["min": <parameter_min_value>],
                                    ["max": <parameter_max_value>]
                                    ["possible_values": <parameter_possible_values_list>]
                                 }
                <parameter_name> is the name of the parameter in the ontology.
                <paramter_type> is a string describing the type of the parameter. It could be "integer", "float" or "text" or "select".
                <parameter_default_value> is the default value of the parameter in the ontology.
                If there is a "min" field in the ontology, the key min will be in the dictionary. <parameter_min_value> is this field's value.
                If there is a "max" field in the ontology, the key max will be in the dictionary. <parameter_max_value> is this field's value.
                If the type is "select", and there is a "possibleValues" field in the ontology, the key possible_values will be in the 
                dictionary. <parameter_possible_values_list> will be this field's list, in the same order. 
        
            The category's list is sorted according to the rank of the category in the ontology.
            The parameter's list in each category is sorted according to the rank of the parameter in the ontology.
            If two parameters have the same category and the same rank, they are sorting according to their name.
            All sorts are ascendent.
        EXAMPLE:
            If there is no parameter, the return is:
            [{ "category_name": None, "parameters": [] }]
            
            If there are two parameters in a category, and one parameter without category, the return is:
            [
                {
                    "category_name": None,
                    "parameters": [{ "name": "a", "type": "text", "value": "" }]
                },
                {
                    "category_name": "cat1",
                    "parameters": [
                        {"name": "b", "type": "integer", "value": 0, "min": 0 },
                        {"name": "c", "type": "select", "value": "Low", "possible_values: ["Low", "Medium", "High"] }
                    ]
                }
            ]
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        query = """ SELECT ?parameter_name ?parameter_type ?parameter_default_value ?parameter_min ?parameter_max 
                            ?parameter_category_name
                    WHERE {
                        ?estimation_method_ontology_uri a orion:EstimationMethod .
                        ?estimation_method_ontology_uri orion:title ?estimation_method_name .
                        ?estimation_method_ontology_uri orion:hasParameter ?estimation_method_parameter_uri .
                        ?estimation_method_parameter_uri orion:name ?parameter_name .
                        ?estimation_method_parameter_uri orion:type ?parameter_type .
                        ?estimation_method_parameter_uri orion:defaultValue ?parameter_default_value .
                        OPTIONAL { ?estimation_method_parameter_uri orion:min ?parameter_min . }
                        OPTIONAL { ?estimation_method_parameter_uri orion:max ?parameter_max . }
                        OPTIONAL {
                            ?estimation_method_parameter_uri orion:category ?estimation_method_parameter_category_uri .
                            ?estimation_method_parameter_category_uri orion:rank ?estimation_method_parameter_category_rank .
                            ?estimation_method_parameter_category_uri orion:name ?parameter_category_name .
                        }
                        OPTIONAL { ?estimation_method_parameter_uri orion:rank ?estimation_method_parameter_rank . }
                    }
                    ORDER BY ?estimation_method_parameter_category_rank ?estimation_method_parameter_rank ?parameter_name
                """
                
        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns}, 
                                                  initBindings = {"estimation_method_name": rdflib.Literal(estimation_method_name)})
        
        previous_parameter_category_name = None
        result = [{"category_name": None, "parameters":[]}]
        for (parameter_name, parameter_type, parameter_default_value, parameter_min, parameter_max, 
             parameter_category_name) in query_result:
                
            parameter_descriptor = {"name": parameter_name.toPython(), "type": parameter_type.toPython(), 
                                     "value": parameter_default_value.toPython()}
            if parameter_min is not None:
                parameter_descriptor["min"] = parameter_min.toPython()
            if parameter_max is not None:
                parameter_descriptor["max"] = parameter_max.toPython()
                
            allowed_types = ["integer", "float", "text", "select"]
            if parameter_descriptor["type"] not in allowed_types:
                raise RuntimeError("The type of the parameter " + parameter_name + " (" + parameter_type + ") is unknown."
                                   + " Allowed types are : " + ", ".join(allowed_types))
                
            if parameter_descriptor["type"] == "select":
                parameter_descriptor["possible_values"] = self._get_estimation_method_parameter_possible_value(parameter_name, orion_ns)
            
            if parameter_category_name != previous_parameter_category_name:
                result.append({"category_name": parameter_category_name.toPython(), "parameters": []})
                previous_parameter_category_name = parameter_category_name
                
            result[-1]["parameters"].append(parameter_descriptor)
                
        return result
    
    def _get_estimation_method_parameter_possible_value(self, parameter_name, orion_ns):
        """
        DESCRIPTION:
            Return the list of possible value for the provided parameter.
        INPUT:
            parameter_name: The name defining the parameter.
            orion_ns: The namespace of the ontology.
        OUTPUT:
            A list with the possible value of the provided parameter.
        """
        query = """ SELECT ?parameter_possible_value
                    WHERE {
                        ?parameter_uri a orion:Parameter .
                        ?parameter_uri orion:name ?parameter_name .
                        ?parameter_uri orion:possibleValues ?parameter_possible_value_list .
                        ?parameter_possible_value_list rdf:rest*/rdf:first ?parameter_possible_value .
                    }
        """

        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns}, initBindings = {"parameter_name": parameter_name})

        return [e.toPython() for (e,) in query_result]

    def _get_estimation_method_used_properties(self, db_infos, alternative_name, property_name, estimation_method_name, 
                                               property_to_estimation_method_name_dict):
        """
        DESCRIPTION:
            Returns a list in which each element is a dependent property of the provided estimation.
        INPUT:
            The estimation is defined by a triplet (alternative, property, estimation method).
            alternative_name: The name of the alternative in the triplet.
            property_name: The name of the property in the triplet.
            estimation_method_name: The name of the estimation method in the triplet.
            property_to_estimation_method_name_dict: A dictionary, containing the name of the dependents properties as keys,
                and the name of the selected estimation method for this dependent property as values. If a dependent property
                is not in the dictionary, the last estimation method used to compute this property will be selected. If the 
                dependent property has never been computed, the first estimation method available will be selected.
        OUTPUT:
            A list in which each element is a dependent property of the provided estimation.
            Each element is a dictionary containing the keys 
                - "name": The name of the dependent property of the estimation method.
                - "estimation_methods_name": The list of all estimation methods available for the dependent property.
                - "selected": The selected estimation method for the dependent property.
                - "value": The value of the dependent property computed with the selected estimation method. If there is
                    none, this field contains the string '---'.
                - "up_to_date": True if the value of the dependent property is up-to-date, False otherwise. A value of a 
                    property is up-to-date if it has been computed after each of its dependents properties.
                - "computed": True if the estimation has already been computed, otherwise False.

        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]

        used_properties_name = self._get_estimation_method_used_properties_name(estimation_method_name)

        alternative_uri = self._get_alternative_uri_from_name(db_infos, alternative_name)
        property_uri = self._get_property_uri_from_name(db_infos, property_name)

        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        estimation_uri = case_db_proxy.get_estimation_uri(user_id=user_id, token=user_token, case_id=case_id,
                                                          alternative_uri=alternative_uri, property_uri=property_uri,
                                                          estimation_method_ontology_id=estimation_method_ontology_id)
        properties_used_to_estimation_method = case_db_proxy.get_estimation_used_properties(user_id=user_id, user_token=user_token,
                                                                                            case_id=case_id, 
                                                                                            estimation_uri=estimation_uri)
        
        result = []
        for current_property_name in used_properties_name:
            
            estimation_method_name_list = self._get_estimation_methods_name(current_property_name)
            if current_property_name in property_to_estimation_method_name_dict:
                selected_estimation_method_for_current_property = property_to_estimation_method_name_dict[current_property_name]
            else:
                current_property_ontology_id = self._get_property_ontology_id_name(current_property_name)
                if current_property_ontology_id in properties_used_to_estimation_method:
                    selected_estimation_method_for_current_property = properties_used_to_estimation_method[current_property_ontology_id]
                    selected_estimation_method_for_current_property = self._get_estimation_method_ontology_id_name(selected_estimation_method_for_current_property, False)
                else:
                    selected_estimation_method_for_current_property = estimation_method_name_list[0]
                
            property_value = self._get_estimation_value(db_infos, alternative_uri, current_property_name,
                                                        selected_estimation_method_for_current_property)
            result.append({"name": current_property_name, "estimation_methods_name": estimation_method_name_list, 
                           "value": property_value["value"], "up_to_date": property_value["up_to_date"], 
                           "computed": property_value["computed"], "selected": selected_estimation_method_for_current_property})
            
        return result
    
    def _get_estimation_method_used_properties_name(self, estimation_method_name):
        """
        DESCRIPTION:
            Returns the dependents properties' name of the provided estimation method.
        INPUT:
            estimation_method_name: The name of the estimation method.
        OUTPUT:
            A list containing the dependents properties' name of the provided estimation method, or an empty list if there is no
            dependents property
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        query = """ SELECT ?property_name
                    WHERE {
                        ?estimation_method_ontology_uri a orion:EstimationMethod .
                        ?estimation_method_ontology_uri orion:title ?estimation_method_name .
                        ?estimation_method_ontology_uri orion:useProperty ?property_ontology_uri .
                        ?property_ontology_uri orion:title ?property_name .
                    }
        """
        
        query_result = self._get_ontology().query(query, initNs = {"orion": orion_ns}, 
                                                  initBindings={"estimation_method_name": rdflib.Literal(estimation_method_name)})
        
        return [e.toPython() for (e,) in query_result]
    
    def _get_estimation_value(self, db_infos, alternative_uri, property_name, estimation_method_name):
        """
        DESCRIPTION:
            Returns the estimated value of the estimation defined by the triplet (alternative, property, estimation method).
        INPUT:
            alternative_uri: The uri of the alternative in the triplet.
            property_name: The name of the property in the triplet.
            estimation_method_name: The name of the estimation method in the triplet. 
        OUTPUT:
            The estimated value as a dictionary containing the keys:
                - "value": The value of the estimation, or self.PROPERTY_VALUE_NOT_COMPUTED_STRING if the estimation has not been
                    computed yet.
                - "up_to_date": A boolean which value is True if this estimation has been computed after all its used estimation,
                    otherwise False. If the estimation has not been computed yet, this value is True.
                - "computed": A boolean which value is True if the estimation has already been computed, otherwise False.
        """
        user_id = db_infos["user_id"]
        user_token = db_infos["user_token"]
        case_id = db_infos["case_id"]
        case_db_proxy = db_infos["case_db_proxy"]
        
        property_uri = self._get_property_uri_from_name(db_infos, property_name)
        estimation_method_ontology_id = self._get_estimation_method_ontology_id_name(estimation_method_name)
        estimated_value = case_db_proxy.get_estimation_value(user_id=user_id, token=user_token, case_id=case_id, 
                                                             alternative_uri=alternative_uri, property_uri=property_uri, 
                                                             estimation_method_ontology_id=estimation_method_ontology_id)
        if estimated_value is None:
            return {"value": self.PROPERTY_VALUE_NOT_COMPUTED_STRING, "up_to_date": True, "computed": False}
    
        estimated_value["computed"] = True       
        return estimated_value
    
    def _get_estimation_method_ontology_id_name(self, estimation_method_attribute, is_attribute_name = True):
        """
        DESCRIPTION:
            Returns the name or the ontology id of the estimation method defined by estimation_method_attribute.
        INPUT:
            estimation_method_attribute: The name or the ontology id of an estimation method.
            is_attribute_name: A boolean, which should be True if estimation_method_attribute is the name of the
                estimation method and False if estimation_method_attribute is the ontology id of the estimation
                method.
        OUTPUT:
            If is_attribute_name is True, returns the ontology id of the estimation method defined by the name
            estimation_method_attribute. Otherwise, returns the name of the estimation method defined by the 
            ontology id estimation_method_attribute.
        ERROR:
            Raise a RuntimeError if no match were found with estimation_method_attribute.
        """
        if is_attribute_name:
            index_returned = 0
            index_look_for = 2
        else:
            index_returned = 2
            index_look_for = 0
            
        orion_ns = rdflib.Namespace(self.orion_ns)
        estimation_methods_list = self._get_ontology_instances(orion_ns.EstimationMethod)
        for estimation_method_tuple in estimation_methods_list:
            if estimation_method_tuple[index_look_for].toPython() == estimation_method_attribute:
                return estimation_method_tuple[index_returned].toPython()
        raise RuntimeError("The provided estimation method attribute " + estimation_method_attribute + " should be in the ontology")
        
        pass
if __name__ == '__main__':
    PropertyModelService(sys.argv[1]).run()


















