'''
Created on 9 aug. 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
import traceback
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint, MicroserviceException

# Standard libraries
import json

# Web server framework
from flask import request
from flask.templating import render_template

# Linked data
import rdflib

class PughService(coach.DecisionProcessService):
    # TODO: Doc string to update
    
    def __init__(self, settings_file_name = None, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)
        self.orion_ns = "http://www.orion-research.se/ontology#"
        self.ontology = None
    
    # Auxiliary methods
    def _get_ontology(self, case_db_proxy = None):
        """
        DESCRIPTION:
            Returns the ontology stored in the database. The query to the database is done only once and the result is stored. 
            Thanks to that, the following times, the stored object can be returned immediately.
        INPUT:
            case_db_proxy: The proxy to access database. It can be omitted if the ontology has already been got from the database.
        OUTPUT:
            The ontology stored in the database. 
        ERROR:
            Throw a TypeError if case_db_proxy is omitted whereas the ontology has not yet been got from the database.
        """
        if not self.ontology:
            self.ontology = rdflib.ConjunctiveGraph()
            self.ontology.parse(data = case_db_proxy.get_ontology(format_ = "ttl"), format = "ttl")
        return self.ontology
    
    
    def _get_ontology_instances(self, class_name = None, case_db_proxy = None, class_name_list = None, returned_information= (0, 1, 2, 3)):
        """
        DESCRIPTION:
            Return a list containing all the instances of the given class in the ontology.
        INPUT:
            class_name: The name of a single class in the ontology. Requested information about all elements of this class present in
                the ontology will be returned. Exactly one of class_name and class_name_list must be provided.
            case_db_proxy: The proxy to access database. It can be omitted if the ontology has already been got from the database.
            class_name_list: A list of class' name in the ontology. Requested information about all elements of these classes present in
                the ontology will be returned. Exactly one of class_name and class_name_list must be provided.
            returned_information: An iterable containing the indexes of the requested informations: 0 for the instances' uri, 1 for the 
                gradeId, 2 for the title and 3 for the description. If there is only one element (e.g. (2,)), a simple list will be returned.
                The elements in the inner list are in the same order than the indexes in returned_information.
        OUTPUT:
            Return a list containing all the instances of the given class in the ontology. Each element of this list provides the requested
            information by returned_information. 
        ERROR:
            A RuntimeError is raised if both class_name and class_name_list are provided, or both are not.
            An IndexError is raised if returned_information contains an integer greater than 3 or smaller than 0.
            A TypeError is raised if returned_information contains a non-integer.
        """
        if (class_name is None and class_name_list is None) or (class_name is not None and class_name_list is not None):
            raise RuntimeError("Exactly one argument among class_name and class_name_list must be provided")
        
        if class_name is not None:
            class_name_list = [class_name]
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        q = """\
        SELECT ?inst ?grade_id ?title ?description
        WHERE {
            ?inst a ?class_name .
            ?inst orion:gradeId ?grade_id .
            ?inst orion:title ?title .
            ?inst orion:description ?description .
        }
        ORDER BY ?grade_id
        """
        
        result = []
        for class_name in class_name_list:
            query_result = self._get_ontology(case_db_proxy).query(q, initNs = { "orion": orion_ns }, 
                                                                   initBindings = { "?class_name": rdflib.URIRef(class_name) })
            class_result = []
            for line in query_result:
                if len(returned_information) == 1:
                    class_result.append(line[returned_information[0]].toPython())
                else:
                    class_result.append([line[index].toPython() for index in returned_information])            
            
            result += class_result
            
        return result
    
    
    def _add_or_replace_criterium(self, db_infos, case_db_proxy, criterium_uri, criterium_name, criterium_weight, criterium_properties_ontology_id_list):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name, object_=None)
        case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name, object_=criterium_name, is_object_uri=False)
        
        case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.weight, object_=None)
        case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.weight, object_=criterium_weight, is_object_uri=False)
        
        case_db_proxy.remove_in_trade_off(**db_infos, subject=None, predicate=orion_ns.criterium_property, object_=criterium_uri)
        for criterium_property_ontology_id in criterium_properties_ontology_id_list:
            property_uri = case_db_proxy.get_property_uri_from_ontology_id(**db_infos, property_ontology_id=criterium_property_ontology_id)
            case_db_proxy.add_in_trade_off(**db_infos, subject=property_uri, predicate=orion_ns.criterium_property, object_=criterium_uri)


    def _delete_criterium(self, db_infos, case_db_proxy, criterium_uri):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        criterium_values_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.value)
        for criterium_value in criterium_values_list:
            case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_value, predicate=None, object_=None)
            case_db_proxy.remove_in_trade_off(**db_infos, subject=None, predicate=None, object_=criterium_value)
        
        case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_uri, predicate=None, object_=None)
        case_db_proxy.remove_in_trade_off(**db_infos, subject=None, predicate=None, object_=criterium_uri)

    def _get_criteria_name_list(self, db_infos, case_db_proxy, trade_off_method_uri):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        criterium_uri_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=trade_off_method_uri, predicate=orion_ns.criterium)
        return [case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name)[0] 
                for criterium_uri in criterium_uri_list]
        
    
    def _get_criterium_uri_from_name(self, db_infos, case_db_proxy, trade_off_method_uri, criterium_name):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        criterium_uri_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=trade_off_method_uri, predicate=orion_ns.criterium)
        for criterium_uri in criterium_uri_list:
            current_criterium_name = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name)[0]        
            if current_criterium_name == criterium_name:
                return criterium_uri
        return None
    
    
    def _get_criteria_properties_estimation_methods(self, db_infos, case_db_proxy, trade_off_method_uri, alternatives_list):
        orion_ns = rdflib.Namespace(self.orion_ns)
        result = []
        
        criteria_uri_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subjec=trade_off_method_uri, predicate=orion_ns.criterium)
        for criterium_uri in criteria_uri_list:
            criterium_properties_uri_list = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.criterium_property,
                                                                                    object_=criterium_uri)
            
        
    

    # Endpoints

    @endpoint("/process_menu", ["GET"], "text/html")
    def process_menu(self):
        return render_template("process_menu.html")


    @endpoint("/select_baseline_dialogue", ["GET"], "text/html")
    def select_baseline_dialogue_transition(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri):
        """
        Endpoint which lets the user select the baseline alternative.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        
        case_db_proxy = self.create_proxy(case_db)
        alternatives = case_db_proxy.get_decision_alternatives(**db_infos)
        baseline_list = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.baseline, object_ = trade_off_method_uri)
        if len(baseline_list) > 1:
            raise RuntimeError("There must be at most one baseline in the database, but {0} were found.".format(len(baseline_list)))
        
        return render_template("select_baseline_dialogue.html", alternatives=alternatives, baseline_list=baseline_list)
        
    
    @endpoint("/select_baseline", ["POST"], "text/html")
    def select_baseline(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri, baseline):
        """
        This method is called using POST when the user presses the select button in the select_baseline_dialogue.
        It gets two form parameters: case_db, which is the url of the case database server, and baseline, which is the id of the selected alternative.
        It changes the selection in the case database, and then shows the matrix dialogue.
        """
        # Write the selection to the database, and show a message
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        alternative_baseline_list = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.baseline, object_=trade_off_method_uri)
        for alternative_baseline in alternative_baseline_list:
            case_db_proxy.remove_in_trade_off(**db_infos, subject=alternative_baseline, predicate=orion_ns.baseline, object_=trade_off_method_uri)
        
        case_db_proxy.add_in_trade_off(**db_infos, subject=baseline, predicate=orion_ns.baseline, object_=trade_off_method_uri)
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id)    
    
    
    @endpoint("/add_criterium_dialogue", ["GET"], "text/html")
    def add_criterium_dialogue_transition(self, case_db):
        """
        Endpoint which shows the dialogue for adding criteria.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy = self.create_proxy(case_db)
        properties_list = self._get_ontology_instances(orion_ns.Property, case_db_proxy, returned_information=(0, 2))
        return render_template("add_criterium_dialogue.html", properties_list=properties_list)
    
    
    @endpoint("/add_criterium", ["POST"], "text/html")
    def add_criterium(self, user_id, delegate_token, case_id, case_db, trade_off_method_uri, criterium_name, criterium_weight):
        """
        This method is called using POST when the user presses the select button in the add_criterium_dialogue.
        It gets three form parameters: case_db, which is the url of the case database server, criterium, which is the name of the new criterium,
        and weight which is its weight. The criteria are stored in the case database as a string which represents a Python dictionary on json format,
        assigned to the criteria attribute of the case node. 
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        try:
            criterium_properties = dict(request.args)["criterium_properties"]
        except KeyError:
            criterium_properties = []

        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        
        criteria_name_list = self._get_criteria_name_list(db_infos, case_db_proxy, trade_off_method_uri)
        if criterium_name in criteria_name_list:
            criterium_uri = self._get_criterium_uri_from_name(db_infos, case_db_proxy, trade_off_method_uri, criterium_name)
        else:
            criterium_uri = case_db_proxy.add_in_trade_off(**db_infos, subject=trade_off_method_uri, predicate=orion_ns.criterium, object_=None)
        
        try:
            self._add_or_replace_criterium(db_infos, case_db_proxy, criterium_uri, criterium_name, criterium_weight, criterium_properties)
        except MicroserviceException:
            return("Compute an estimation for each property you want to add.")
        
        return "Criterium added!"
    
    @endpoint("/change_criterium_dialogue", ["GET"], "text/html")
    def change_criterium_dialogue_transition(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri, selected_criterium_name=""):
        """
        Endpoint which shows the dialogue for changing criteria.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        criteria_name_list = self._get_criteria_name_list(db_infos, case_db_proxy, trade_off_method_uri)
        if selected_criterium_name not in criteria_name_list:
            selected_criterium_name = criteria_name_list[0]
            
        selected_criterium_uri = self._get_criterium_uri_from_name(db_infos, case_db_proxy, trade_off_method_uri, selected_criterium_name)
        selected_criterium_weight = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=selected_criterium_uri, predicate=orion_ns.weight)[0]
        
        selected_criterium_properties_uri = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.criterium_property, 
                                                                                    object_=selected_criterium_uri)
        selected_criterium_properties_ontology_id = (
            case_db_proxy.get_properties_ontology_id_from_uri(**db_infos, properties_uri_list=selected_criterium_properties_uri))
            
        properties_list = self._get_ontology_instances(orion_ns.Property, case_db_proxy, returned_information=(0, 2))
        
        return render_template("change_criterium_dialogue.html", criteria_name_list=criteria_name_list, properties_list=properties_list,
                               selected_criterium_name=selected_criterium_name, selected_criterium_weight=selected_criterium_weight,
                               selected_criterium_properties=selected_criterium_properties_ontology_id)
    
    
    @endpoint("/manage_change_criterium_form", ["POST"], "text/html")
    def manage_change_criterium_form(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri, criterium, new_name, new_weight, action):
        """
        This method is called using POST when the user presses either the change criterium or delete criterium buttons in the 
        change_criterium_dialogue. The form parameters are case_db and case_id, the current name of the criterium to change, 
        optionally a new name and optionally a new weight. There are two submit buttons in the form, and the one selected is indicated
        in the button parameter. The method modifies the list of criteria in the root node, and also the ranking in each
        alternative. 
        """
        try:
            criterium_properties = dict(request.args)["criterium_properties"]
        except KeyError:
            criterium_properties = []
        
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        criterium_uri = self._get_criterium_uri_from_name(db_infos, case_db_proxy, trade_off_method_uri, criterium)
        if action == "Change criterium":
            self._add_or_replace_criterium(db_infos, case_db_proxy, criterium_uri, new_name, new_weight, criterium_properties)
            return "Criterium changed!"
        elif action == "Delete criterium":
            self._delete_criterium(db_infos, case_db_proxy, criterium_uri)
            return "Criterium deleted!"
        elif action == "select_criterium":
            return self.change_criterium_dialogue_transition(user_id, delegate_token, case_db, case_id, trade_off_method_uri, criterium)
        else:
            raise RuntimeError("Unknown action name: {0}.".format(action))
    
    
    @endpoint("/matrix_dialogue", ["GET"], "text/html")
    def matrix_dialogue_transition(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri):
        """
        Endpoint which shows the Pugh matrix dialogue.
        """
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        alternatives_list = case_db_proxy.get_decision_alternatives(**db_infos)
        criteria_nested_list = self._get_criteria_properties_estimation_methods(db_infos, case_db_proxy, trade_off_method_uri, 
                                                                                alternatives_list)
        
        return render_template("matrix_dialogue.html", alternatives_list=alternatives_list, criteria_nested_list=criteria_nested_list)
    
    
    @endpoint("/change_rating", ["POST"], "text/html")
    def change_rating(self, user_id, delegate_token, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the Pugh matrix dialogue. It updates the values
        of the ranking of each alternative according to the current values in the dialogue.
        """
        # Get alternatives from the database
        case_db_proxy = self.create_proxy(case_db)

        decision_alternatives = case_db_proxy.get_decision_alternatives(user_id = user_id, token = delegate_token, case_id = case_id)
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = self.get_criteria(user_id, delegate_token, case_db, case_id).keys()

        # For each alternative, build a map from criteria to value and write it to the database
        for a in alternative_ids:
            ranking = { c : request.values[str(a) + ":" + c] for c in criteria }
            self.set_alternative_ranking(user_id, delegate_token, case_db, case_id, a, ranking)

        # Show the updated matrix        
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id)    
        

if __name__ == '__main__':
    PughService(sys.argv[1]).run()