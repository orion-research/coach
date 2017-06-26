"""
Created on June 22, 2016

@author: Jan Carlson

The context model service
"""
from COACH.build_coach_deployments import context_model

"""
TODO:

- Only the first of multiple selection alternatives are sent when the button is pressed.
Sending it using method="get" includes all selected alternatives. Question is when duplicates of the same parameter are discarded


- Button size (MAC bug):
Possible workaround, but not so nice:
input[type=submit] {
  font-weight: bold;
  font-size: 150%;
}

- Some selections should also have a text field (treat as a separate type "multiother")?

- Should be possible to have a "no answer" value also in the radio buttons.

- Now each context entry is saved as a separate case fact. Is it better to save the whole context as a single fact?

- Now all values are represented as strings when stored in the case fact (e.g., "Low" or "Aerospace/Aviation"). Is this ok?

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

class ContextModelService(coach.Microservice):
      
      
    def __init__(self, settings_file_name = None, working_directory = None):
        
        super().__init__(settings_file_name, working_directory = working_directory)
      
        # Store case database connection, using user_id and user_token as default parameters to all endpoint calls.
        #self.case_db_proxy = self.create_proxy(self.get_setting("database"))

        self.ontology = None
        self.orion_ns = "http://www.orion-research.se/ontology#"


    def get_ontology(self, db_infos = None):
        """
        Returns the ontology. If the ontology has not been loaded yet, it is loaded and stored before being returned.
        """
        if not self.ontology:
            case_db_proxy = db_infos["case_db_proxy"]
            self.ontology = rdflib.ConjunctiveGraph()
            self.ontology.parse(data = case_db_proxy.get_ontology(format = "ttl"), format = "ttl")
        return self.ontology
        
        

    @endpoint("/edit_context_dialogue", ["GET"], "text/html")
    def edit_context_dialogue_transition(self, user_id, user_token, case_db, case_id):
        """
        Endpoint which lets the user edit general context information.
        """
        
        case_db_proxy = self.create_proxy(case_db)
       
        values = {'C' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_C"),
                  'O' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_O"),
                  'P' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_P"),
                  'S' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_S"),
                  'M' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_M"),
                  'B' : case_db_proxy.get_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_B")
                  }
        
        return render_template("edit_context_dialogue.html", values = values)     



    @endpoint("/edit_context", ["POST"], "text/html")
    def edit_context(self, user_id, user_token, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the edit_context_dialogue_transition.
        It gets several form parameters: 
        case_id : The ID of the current case
        context_text : The text entered in the main context text area
        It writes the new context information to the database, and then returns a status message to be shown in the main dialogue window.
        """
        # DEBUGGING
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        print("XXXX str(request.values)) XXX")
        print(str(request.values))
        print("XXXX request.form XXX")
        print(request.form)
        print("XXXX request.args XXX")
        print(request.args)
        print("XXXX request.data XXX")
        print(request.data)
        print("XXXX request.headers XXX")
        print(request.headers)
        print("XXXX request.method XXX")
        print(request.method)
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        
        
        # Write the new context information to the database.
        case_db_proxy = self.create_proxy(case_db)
        
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_C", value = request.values["C-text"] if "C-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_O", value = request.values["O-text"] if "O-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_P", value = request.values["P-text"] if "P-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_S", value = request.values["S-text"] if "S-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_M", value = request.values["M-text"] if "M-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = user_token, case_id = case_id, name = "context_B", value = request.values["B-text"] if "B-text" in request.values else "")

        return "Context information (general) saved."     

    def _context_category_dialogue(self, db_infos, category_name, category, edit_endpoint):
        return render_template(
            "context_category_dialogue.html",
            category_name = category_name,
            entries = category,
            edit_endpoint = edit_endpoint,
            values = {})
    
    @endpoint("/context_organization_dialogue", ["GET"], "text/html")
    def context_organization_dialogue(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        organization_context = self._get_context_from_ontology(db_infos, orion_ns.OrganizationProperty, orion_ns)
        context_values = case_db_proxy.get_context(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                   context_predicate=orion_ns.organization)
        self._update_context_description(context_values, organization_context)
        
        return self._context_category_dialogue(db_infos, "Organization", organization_context, "edit_context_organization")
    
    @endpoint("/context_product_dialogue", ["GET"], "text/html")
    def context_product_dialogue(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        product_context = self._get_context_from_ontology(db_infos, orion_ns.ProductProperty, orion_ns)
        context_values = case_db_proxy.get_context(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                   context_predicate=orion_ns.product)
        self._update_context_description(context_values, product_context)
        
        return self._context_category_dialogue(db_infos, "Product", product_context, "edit_context_product")
    
    @endpoint("/context_stakeholder_dialogue", ["GET"], "text/html")
    def context_stakeholder_dialogue(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        stakeholder_context = self._get_context_from_ontology(db_infos, orion_ns.StakeholderProperty, orion_ns)
        context_values = case_db_proxy.get_context(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                   context_predicate=orion_ns.stakeholder)
        self._update_context_description(context_values, stakeholder_context)
        
        return self._context_category_dialogue(db_infos, "Stakeholder", stakeholder_context, "edit_context_stakeholder")
        
    @endpoint("/context_methods_dialogue", ["GET"], "text/html")
    def context_methods_dialogue(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        methods_context = self._get_context_from_ontology(db_infos, orion_ns.DevelopmentMethodAndTechnologyProperty, orion_ns)
        context_values = case_db_proxy.get_context(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                   context_predicate=orion_ns.method)
        self._update_context_description(context_values, methods_context)
        
        return self._context_category_dialogue(db_infos, "Development methods and Technology", methods_context, "edit_context_methods")
        
    @endpoint("/context_business_dialogue", ["GET"], "text/html")
    def context_business_dialogue(self, user_id, user_token, case_db, case_id): 
        case_db_proxy = self.create_proxy(case_db)
        db_infos = {"case_id": case_id, "user_id": user_id, "user_token": user_token, "case_db_proxy": case_db_proxy}
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        business_context = self._get_context_from_ontology(db_infos, orion_ns.MarketAndBusinessProperty, orion_ns)
        context_values = case_db_proxy.get_context(user_id=user_id, user_token=user_token, case_id=case_id, 
                                                   context_predicate=orion_ns.business)
        self._update_context_description(context_values, business_context)
        
        return self._context_category_dialogue(db_infos, "Market and business", business_context, "edit_context_business")
        
    def _get_context_from_ontology(self, db_infos, context_category, orion_ns):
        query = """ SELECT ?entry_ontology_uri ?entry_grade_id ?entry_description ?entry_guideline ?entry_type ?entry_default_value ?entry_min 
                        ?entry_max
                    WHERE {
                        ?entry_ontology_uri a ?context_category .
                        ?entry_ontology_uri orion:gradeId ?entry_grade_id .
                        ?entry_ontology_uri orion:description ?entry_description .
                        ?entry_ontology_uri orion:guideline ?entry_guideline .
                        ?entry_ontology_uri orion:type ?entry_type .
                        OPTIONAL {
                            ?entry_ontology_uri orion:defaultValue ?entry_default_value .
                        }
                        OPTIONAL {
                            ?entry_ontology_uri orion:min ?entry_min .
                        }
                        OPTIONAL {
                            ?entry_ontology_uri orion:max ?entry_max .
                        }
                    }
                    ORDER BY ?entry_grade_id
        """
        
        result_query = self.get_ontology(db_infos).query(query, initNs = {"orion": orion_ns}, 
                                                         initBindings = {"context_category": rdflib.URIRef(context_category)})
        
        result = []
        for (entry_ontology_uri, entry_grade_id, entry_description, entry_guideline, entry_type, entry_default_value, entry_min, 
             entry_max) in result_query:
            entry_descriptor = {"id": entry_grade_id.toPython(),
                                "description": entry_description.toPython(),
                                "guideline": entry_guideline.toPython(),
                                "type": entry_type.toPython()}
            if entry_default_value is not None:
                entry_descriptor["value"] = entry_default_value.toPython()
            if entry_min is not None:
                entry_descriptor["min"] = entry_min.toPython()
            if entry_max is not None:
                entry_descriptor["max"] = entry_max.toPython()
            
            if entry_descriptor["type"] in ["single_select", "multi_select"]:
                entry_descriptor["possible_values"] = self._get_entry_possible_value(entry_ontology_uri, orion_ns)
            
            allowed_types = ["integer", "float", "text", "single_select", "multi_select"]
            if entry_descriptor["type"] not in allowed_types:
                raise RuntimeError("The type of the entry " + entry_descriptor["ontology_uri"] + " (" + entry_descriptor["type"]
                                   + ") is unknown. Allowed types are : " + ", ".join(allowed_types))
            
            result.append(entry_descriptor)
        return result
    
    def _get_entry_possible_value(self, entry_ontology_uri, orion_ns):
        query = """ SELECT ?entry_possible_value
                    WHERE {
                        ?entry_ontology_uri orion:possibleValues ?entry_possible_value_list .
                        ?entry_possible_value_list rdf:rest*/rdf:first ?entry_possible_value .
                    }
        """
        
        query_result = self.get_ontology().query(query, initNs = {"orion": orion_ns}, initBindings = {"entry_ontology_uri": entry_ontology_uri})
        return [e.toPython() for (e,) in query_result]
    
    def _update_context_description(self, context_values, context_description):
        for context_entry in context_description:
            try:
                if len(context_values[context_entry["id"]]) == 1:
                    context_entry["value"] = context_values[context_entry["id"]][0]
                else:
                    context_entry["value"] = context_values[context_entry["id"]]
            except KeyError:
                pass
    
    def _get_context_values_dict_from_request(self):
        contex_values_dict = dict(request.args)
        del contex_values_dict["case_id"]
        del contex_values_dict["knowledge_repository"]
        del contex_values_dict["user_id"]
        del contex_values_dict["user_token"]
        del contex_values_dict["case_db"]
        return contex_values_dict
    
    @endpoint("/edit_context_organization", ["POST"], "text/html")
    def edit_context_organization(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        context_values_dict = self._get_context_values_dict_from_request()
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy.save_context(user_id=user_id, user_token=user_token, case_id=case_id, context_predicate=orion_ns.organization,
                                   context_values_dict=context_values_dict)
        return "Context information (organization) saved."

    @endpoint("/edit_context_product", ["POST"], "text/html")
    def edit_context_product(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        context_values_dict = self._get_context_values_dict_from_request()
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy.save_context(user_id=user_id, user_token=user_token, case_id=case_id, context_predicate=orion_ns.product,
                                   context_values_dict=context_values_dict)
        return "Context information (product) saved."

    @endpoint("/edit_context_stakeholder", ["POST"], "text/html")
    def edit_context_stakeholder(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        context_values_dict = self._get_context_values_dict_from_request()
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy.save_context(user_id=user_id, user_token=user_token, case_id=case_id, context_predicate=orion_ns.stakeholder,
                                   context_values_dict=context_values_dict)
        return "Context information (stakeholder) saved."

    @endpoint("/edit_context_methods", ["POST"], "text/html")
    def edit_context_methods(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        context_values_dict = self._get_context_values_dict_from_request()
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy.save_context(user_id=user_id, user_token=user_token, case_id=case_id, context_predicate=orion_ns.method,
                                   context_values_dict=context_values_dict)
        return "Context information (method) saved."
    
    @endpoint("/edit_context_business", ["POST"], "text/html")
    def edit_context_business(self, user_id, user_token, case_db, case_id):
        case_db_proxy = self.create_proxy(case_db)
        context_values_dict = self._get_context_values_dict_from_request()
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_db_proxy.save_context(user_id=user_id, user_token=user_token, case_id=case_id, context_predicate=orion_ns.business,
                                   context_values_dict=context_values_dict)
        return "Context information (business) saved."
if __name__ == '__main__':
    ContextModelService(sys.argv[1]).run()
