'''
Created on 9 aug. 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint, MicroserviceException


# Web server framework
from flask import request
from flask.templating import render_template

# Linked data
import rdflib

class PughService(coach.DecisionProcessService):
    PROPERTY_NOT_ADDED_STRING = ""
    PROPERTY_VALUE_NOT_COMPUTED_STRING = "---"
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
    
    
    def _get_estimation_method_property_ontology_id_name(self, class_attribute, is_class_property, is_attribute_name=True, case_db_proxy=None):
        """
        DESCRIPTION:
            Returns the name or the ontology id of the estimation method or the property defined by class_attribute.
        INPUT:
            class_attribute: The name or the ontology id of an estimation method or a property.
            is_class_property: A boolean, which is True if we are looking for a property attribute, and False if 
                we are looking for an estimation method attribute.
            is_attribute_name: A boolean, which should be True if class_attribute is the name of the
                class and False if class_attribute is the ontology id of the class.
        OUTPUT:
            If is_attribute_name is True, returns the ontology id of the class defined by the name
            class_attribute. Otherwise, returns the name of the class defined by the 
            ontology id class_attribute.
        ERROR:
            Raise a RuntimeError if no match were found with class_attribute.
        """
        if is_attribute_name:
            index_returned = 0
            index_look_for = 2
        else:
            index_returned = 2
            index_look_for = 0
        
        orion_ns = rdflib.Namespace(self.orion_ns)

        if is_class_property:
            orion_class = orion_ns.Property
        else:
            orion_class = orion_ns.EstimationMethod
            
        class_list = self._get_ontology_instances(orion_class, case_db_proxy)
        for class_tuple in class_list:
            if class_tuple[index_look_for] == class_attribute:
                return class_tuple[index_returned]
        raise RuntimeError("The provided attribute " + class_attribute + " should be in the ontology")

    def _get_estimation_methods_name(self, property_name, case_db_proxy):
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
        property_ontology_id = self._get_estimation_method_property_ontology_id_name(property_name, True, True)
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
        
        query_result = self._get_ontology(case_db_proxy).query(query, initNs = {"orion": orion_ns}, 
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
    
    
    def _add_or_replace_criterium(self, db_infos, case_db_proxy, criterium_uri, criterium_name, criterium_weight, criterium_properties_ontology_id_list):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        try:
            case_db_proxy.remove_in_trade_off(**db_infos, subject=None, predicate=orion_ns.criterium_property, object_=criterium_uri)
            for criterium_property_ontology_id in criterium_properties_ontology_id_list:
                property_uri = case_db_proxy.get_property_uri_from_ontology_id(**db_infos, property_ontology_id=criterium_property_ontology_id)
                case_db_proxy.add_in_trade_off(**db_infos, subject=property_uri, predicate=orion_ns.criterium_property, object_=criterium_uri)
    
            case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name, object_=None)
            case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name, object_=criterium_name, is_object_uri=False)
            
            case_db_proxy.remove_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.weight, object_=None)
            case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.weight, object_=criterium_weight, is_object_uri=False)
        except MicroserviceException:
            self._delete_criterium(db_infos, case_db_proxy, criterium_uri)
            raise


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
    
    
    def _get_criteria_properties_estimation_methods(self, db_infos, case_db_proxy, trade_off_method_uri):
        orion_ns = rdflib.Namespace(self.orion_ns)
        alternatives_list = case_db_proxy.get_decision_alternatives(**db_infos)
        alternatives_uri_to_name_dict = {alternative_uri: alternative_name for (alternative_name, alternative_uri) in alternatives_list}
        result = []
        
        criteria_uri_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=trade_off_method_uri, predicate=orion_ns.criterium)
        for criterium_uri in criteria_uri_list:
            criterium_name = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.name)[0]
            criterium_weight = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.weight)[0]
            criterium_ranking = self._get_criterium_ranking(db_infos, case_db_proxy, criterium_uri, alternatives_uri_to_name_dict)
            result.append({"criterium_name": criterium_name, "criterium_weight": criterium_weight, "criterium_properties_list": [], 
                           "ranking": criterium_ranking})
            
            criterium_properties_uri_list = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.criterium_property,
                                                                                    object_=criterium_uri)
            for property_uri in criterium_properties_uri_list:
                properties_estimation_method = self._get_properties_estimation_methods(db_infos, case_db_proxy, property_uri, alternatives_list)
                result[-1]["criterium_properties_list"].append(properties_estimation_method)
        
        return result
    
    
    def _get_criterium_ranking(self, db_infos, case_db_proxy, criterium_uri, alternatives_uri_to_name_dict):
        orion_ns = rdflib.Namespace(self.orion_ns)
        criterium_values_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.value)
        
        result = {}
        for criterium_value_uri in criterium_values_list:
            criterium_value = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_value_uri, predicate=orion_ns.value)[0]
            alternative_uri = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.criterium_alternative, 
                                                                      object_=criterium_value_uri)[0]
            alternative_name = alternatives_uri_to_name_dict[alternative_uri]
            
            result[alternative_name] = criterium_value
            
        return result
            
    def _get_properties_estimation_methods(self, db_infos, case_db_proxy, property_uri, alternatives_list):
        property_ontology_id = case_db_proxy.get_property_ontology_id_from_uri(**db_infos, property_uri=property_uri)
        property_name = self._get_estimation_method_property_ontology_id_name(property_ontology_id, True, False, case_db_proxy)

        estimation_methods_name_list = self._get_estimation_methods_name(property_name, case_db_proxy)
        estimation_methods = []
        for estimation_method_name in estimation_methods_name_list:
            current_em = self._get_estimation_method_values(db_infos, case_db_proxy, estimation_method_name, property_uri, alternatives_list)
            estimation_methods.append(current_em)
        
        return {"property_name": property_name, "estimation_methods": estimation_methods}
    
    
    def _get_estimation_method_values(self, db_infos, case_db_proxy, estimation_method_name, property_uri, alternatives_list):
        estimation_method_ontology_id = self._get_estimation_method_property_ontology_id_name(estimation_method_name, False, True)
        
        linked_alternatives_list_uri = case_db_proxy.get_alternative_from_property_uri(**db_infos, property_uri=property_uri)
        
        estimation_methods_values = []
        for (_, alternative_uri) in alternatives_list:
            if alternative_uri in linked_alternatives_list_uri:
                db_result = case_db_proxy.get_estimation_value(**db_infos, 
                                                               alternative_uri=alternative_uri, property_uri=property_uri, 
                                                               estimation_method_ontology_id=estimation_method_ontology_id)
                if db_result is None:
                    db_result = {"value": self.PROPERTY_VALUE_NOT_COMPUTED_STRING, "up_to_date": True}
            else:
                db_result = {"value": self.PROPERTY_NOT_ADDED_STRING, "up_to_date": True}
            
            estimation_methods_values.append({"value": db_result["value"], "up_to_date": db_result["up_to_date"]})
        
        return {"estimation_method_name": estimation_method_name, "estimated_values": estimation_methods_values}
            
    
    def _add_criterium_value(self, db_infos, case_db_proxy, trade_off_method_uri, criterium_name, alternative_uri, criterium_value):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        criterium_uri = self._get_criterium_uri_from_name(db_infos, case_db_proxy, trade_off_method_uri, criterium_name)
        criterium_values_uri_list = case_db_proxy.get_objects_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.value)
        for criterium_value_uri in criterium_values_uri_list:
            link_alternative_uri = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.criterium_alternative,
                                                                           object_=criterium_value_uri)
            
            if link_alternative_uri == alternative_uri:
                case_db_proxy.set_in_trade_off(**db_infos, subject=criterium_value_uri, predicate=orion_ns.value, object_=criterium_value)
                return
            
        # A value node for this criterium and alternative does not exist yet, a new one will be created
        criterium_value_uri = case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_uri, predicate=orion_ns.value, object_=None)
        case_db_proxy.add_in_trade_off(**db_infos, subject=criterium_value_uri, predicate=orion_ns.value, object_=criterium_value, 
                                       is_object_uri=False)
        case_db_proxy.add_in_trade_off(**db_infos, subject=alternative_uri, predicate=orion_ns.criterium_alternative, 
                                       object_=criterium_value_uri)

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
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id, trade_off_method_uri)    
    
    
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
            return "Compute an estimation for each property you want to add."
        
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
        if len(criteria_name_list) == 0:
            return "Add a criterium before wanting to change one"
        
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
            try:
                self._add_or_replace_criterium(db_infos, case_db_proxy, criterium_uri, new_name, new_weight, criterium_properties)
            except MicroserviceException:
                return "Compute an estimation for each property you want to add."
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
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        case_db_proxy = self.create_proxy(case_db)
        
        alternatives_list = case_db_proxy.get_decision_alternatives(**db_infos)
        criteria_nested_list = self._get_criteria_properties_estimation_methods(db_infos, case_db_proxy, trade_off_method_uri)
        try:
            baseline_uri = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.baseline, object_=trade_off_method_uri)[0]
        except IndexError:
            baseline_uri = None
            
        return render_template("matrix_dialogue.html", alternatives_list=alternatives_list, baseline_uri=baseline_uri,
                               criteria_nested_list=criteria_nested_list)
    
    
    @endpoint("/change_rating", ["POST"], "text/html")
    def change_rating(self, user_id, delegate_token, case_db, case_id, trade_off_method_uri):
        """
        This method is called using POST when the user presses the save button in the Pugh matrix dialogue. It updates the values
        of the ranking of each alternative according to the current values in the dialogue.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"user_id": user_id, "token": delegate_token, "case_id": case_id}
        request_values = request.values.to_dict()

        try:
            baseline_uri = case_db_proxy.get_subjects_in_trade_off(**db_infos, predicate=orion_ns.baseline, object_=trade_off_method_uri)[0]
        except IndexError:
            baseline_uri = None
            
        alternatives_list = case_db_proxy.get_decision_alternatives(**db_infos)
        criteria_name_list = self._get_criteria_name_list(db_infos, case_db_proxy, trade_off_method_uri)
        for (_, alternative_uri) in alternatives_list:
            if alternative_uri == baseline_uri:
                continue # Baseline has always a 0 value, but we want to preserve an ancient value set by the user, if any.
            
            for criterium_name in criteria_name_list:
                try:
                    criterium_value = request_values["{0}_{1}".format(alternative_uri, criterium_name)]
                except KeyError:
                    criterium_value = 0
                
                self._add_criterium_value(db_infos, case_db_proxy, trade_off_method_uri, criterium_name, alternative_uri, criterium_value)
        
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id, trade_off_method_uri)    
        

if __name__ == '__main__':
    PughService(sys.argv[1]).run()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    