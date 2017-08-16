'''
Created on 23 dec. 2016

@author: Jakob Axelsson
'''

# Standard libraries
from hashlib import sha1
import hmac
import ipaddress
import json
import os
import subprocess

# Coach modules
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Web server framework
from flask import request, session, abort
from flask.templating import render_template

import requests

# Linked data
import rdflib

class InteractionService(coach.Microservice):
    
    """
    RootService implements the overall workflow manager and decision case manager. It is configured with links to 
    a number of directories, which are used for searching for other services. It contains the basic
    functionality for logging in, registering users, creating and closing decision cases, attaching
    users to a decision case, and selecting the decision process. Every installation of COACH has exactly one instance of this class.
    """
    
    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initialize the RootService object. The secret_args argument should be a list of three strings:
        1. The database user name.
        2. The database password.
        3. The session encryption key.
        These are kept outside the settings file to ensure that they do not spread when files are shared in a repository.
        """
        
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file_:
            fileData = file_.read()
        secret_data = json.loads(fileData)

        # Setup encryption for settings cookies
        self.ms.secret_key = secret_data["secret_key"]

        # Setup key for GitHub webhook
        self.github_key = secret_data["github_key"]

        # Store authentication service connection
        self.authentication_service_proxy = self.create_proxy(self.get_setting("authentication_service"))

        # Store case database connection, using user_id and user_token as default parameters to all endpoint calls.
        self.case_db_proxy = self.create_proxy(self.get_setting("database"))
        self.knowledge_repository_proxy = self.create_proxy(self.get_setting("knowledge_repository"))

        # Store point to service directories
        self.service_directory_proxies = [self.create_proxy(sd) for sd in self.get_setting("service_directories")]

        # Placeholder for the ORION ontology. Since the ontology is loaded from the case database, it is not given a value here.
        # This is because it cannot be assumed that the case database is up and running at this point.
        # Instead, the ontology is loaded upon the first call to the method self.get_ontology(), which should be used for accessing it.
        self.ontology = None
        self.orion_ns = "http://www.orion-research.se/ontology#"


    @endpoint("/get_version", ["GET"], "text/html")
    def get_version(self):
        """
        Returns the version of the software running. It fetches this information from git.
        """
        try:
            return subprocess.check_output(["git", "describe", "--all", "--long"], cwd = self.working_directory).decode("ascii")[-7:]
        except:
            return "No version information available"


    def get_ontology(self):
        """
        Returns the ontology used by the interaction service. If the ontology has not been loaded yet, it is loaded and stored before being returned.
        """
        if not self.ontology:
            self.ontology = rdflib.ConjunctiveGraph()
            self.ontology.parse(data = self.case_db_proxy.get_ontology(format_ = "ttl"), format = "ttl")
        return self.ontology
        
    
    @endpoint("/", ["GET"], "text/html")
    def initial_transition(self):
        # Store the software version in the session object
        session["version"] = self.get_version()
        return render_template("initial_dialogue.html")


    @endpoint("/create_user_dialogue", ["GET"], "text/html")
    def create_user_dialogue_transition(self):
        return render_template("create_user_dialogue.html")


    @endpoint("/reset_password_dialogue", ["GET"], "text/html")
    def reset_password_dialogue_transition(self):
        return render_template("reset_password_dialogue.html")
    
    
    @endpoint("/reset_password", ["POST"], "text/html")
    def reset_password(self, email):
        self.authentication_service_proxy.reset_password(email = email)
        return render_template("initial_dialogue.html")
    
    
    @endpoint("/main_menu", ["GET", "POST"], "text/html")
    def main_menu_endpoint(self):
        """
        Endpoint defining transitions to the main menu.
        """
        return self.main_menu_transition()
    
    
    def main_menu_transition(self, **kwargs):
        """
        Internal function used for transition to the main menu. 
        If the case in the database has a decision method selected, its process method is fetched and included in the context.
        """
        context = kwargs
        
        if "case_id" in session:
            orion_ns = rdflib.Namespace(self.orion_ns)
            db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
            case_id = db_infos["case_id"]
            
            selected_decision_process = self.case_db_proxy.get_selected_trade_off_method(**db_infos)
            if selected_decision_process:
                decision_process_proxy = self.create_proxy(selected_decision_process)
                context["process_menu"] = decision_process_proxy.process_menu()
                
            context["is_case_open"] = self.case_db_proxy.get_value(**db_infos, subject=case_id, predicate=orion_ns.close, object_=None, 
                                                                   any_=False)
            context["is_case_open"] = not context["is_case_open"]
        return render_template("main_menu.html", **context)


    @endpoint("/decision_process_request", ["GET", "POST"], "text/html")
    def decision_process_request(self):
        """
        Endpoint which relays a request to the decision process associated with the currently active case.
        It always passes the current decision case id as a parameter in the request.
        It requests a delegate token from the authentication server, and then revokes it after the call.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        
        trade_off_method_url = self.case_db_proxy.get_selected_trade_off_method(user_id = user_id, user_token = user_token, case_id = case_id)
        delegate_token = self.authentication_service_proxy.get_delegate_token(user_id = user_id, user_token = user_token, case_id = case_id)
        
        if trade_off_method_url:
            trade_off_method_uri = self.case_db_proxy.get_value(user_id=user_id, user_token=user_token, case_id=case_id, subject=case_id,
                                                                predicate=orion_ns.selected_trade_off_method, object_=None, any_=False)
            
            # Using request.value is not good, because when there are multiple value for one argument, only the first one is used instead
            # of creating a list.
            params = dict(request.form)
            params.update(request.args)
            if len(params) != len(request.args) + len(request.form):
                raise RuntimeError("Overlapping arguments between args and form")

            del params["endpoint"]
            params["user_id"] = user_id
            params["delegate_token"] = delegate_token
            params["case_db"] = self.get_setting("database")
            params["case_id"] = case_id
            params["directories"] = json.dumps(self.get_setting("service_directories"))
            params["knowledge_repository"] = self.get_setting("knowledge_repository")
            params["trade_off_method_uri"] = trade_off_method_uri
            response = requests.request(request.method, trade_off_method_url + "/" + request.values["endpoint"], params = params)
            self.authentication_service_proxy.revoke_delegate_token(user_id = session["user_id"], user_token = session["user_token"])
            return self.main_menu_transition(main_dialogue = response.text)
        else:
            raise RuntimeError("No decision process selected")
        
    
    @endpoint("/context_model_request", ["GET", "POST"], "text/html")
    def context_model_request(self):
        """
        Endpoint which relays a request to the context model.
        It always passes the current decision case database url and case id as a parameter in the request.
        """
        context_service = self.get_setting("context_service")

        # Using request.value is not good, because when there are multiple value for one argument, only the first one is used instead
        # of creating a list.
        params = dict(request.form)
        params.update(request.args)
        if len(params) != len(request.args) + len(request.form):
            raise RuntimeError("Overlapping arguments between args and form")

        del params["endpoint"]
        params["user_id"] = session["user_id"]
        params["user_token"] = session["user_token"]
        params["case_db"] = self.get_setting("database")
        params["case_id"] = session["case_id"]
        params["knowledge_repository"] = self.get_setting("knowledge_repository")
        response = requests.request(request.method, context_service + "/" + request.values["endpoint"], 
                                    params = params)
        return self.main_menu_transition(main_dialogue = response.text)


    @endpoint("/property_model_request", ["GET", "POST"], "text/html")
    def property_model_request(self):
        """
        Endpoint which relays a request to the property model.
        It always passes the current decision case database url and case id as a parameter in the request.
        """
        property_service = self.get_setting("property_service")
        params = request.values.to_dict()
        
        del params["endpoint"]
        params["user_id"] = session["user_id"]
        params["user_token"] = session["user_token"]
        params["case_db"] = self.get_setting("database")
        params["case_id"] = session["case_id"]
        params["knowledge_repository"] = self.get_setting("knowledge_repository")
        
        response = requests.request(request.method, property_service + "/" + request.values["endpoint"], 
                                    params = params)
        return self.main_menu_transition(main_dialogue = response.text)
    
    @endpoint("/create_case_dialogue", ["GET"], "text/html")
    def create_case_dialogue_transition(self):
        dialogue = render_template("create_case_dialogue.html")
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/load_case_dialogue", ["GET"], "text/html")
    def load_case_dialogue_transition(self):
        # Create links to the user's cases
        user_cases_db = self.case_db_proxy.user_cases(user_id = session["user_id"], user_token = session["user_token"])
        user_cases_kr = self.knowledge_repository_proxy.get_cases(user_id = session["user_id"])
        
        opened_cases = user_cases_db["opened_cases"]
        closed_cases = user_cases_db["closed_cases"]
        exported_cases = [user_case for user_case in user_cases_kr if user_case not in opened_cases if user_case not in closed_cases]
        
        dialogue = render_template("load_case_dialogue.html", opened_cases=opened_cases, closed_cases=closed_cases, exported_cases=exported_cases)
        return self.main_menu_transition(main_dialogue = dialogue)

    @endpoint("/case_status_dialogue", ["GET"], "text/html")
    def case_status_dialogue_transition(self):
        """
         Get case description
        """  
        activities = {}
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_id = session["case_id"]
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": case_id}
        
        activities["case_description"] = {
            "link" : "/edit_case_description_dialogue",
            "name" : "Describe case",
            "status" : "Started"} # The case description is done when the user creates a new case.

        activities["stakeholders"] = {
            "link" : "/add_stakeholder_dialogue",
            "name" : "Add stakeholders",
            "status" : "Not started"}
        roles_uri = self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.role)
        # The case owner is always a stakeholder. So we can safely access the first element of the list, as it will never be empty.
        # Each role node has two link by default: the person who has the role, and a link to say that it is a role
        if len(roles_uri) > 1 or len(self.case_db_proxy.get_predicate_objects(**db_infos, subject=roles_uri[0])) > 2:
            activities["stakeholders"]["status"] = "Started"
            
        activities["goal"] = {
            "link" : "/edit_goal_description_dialogue",
            "name" : "Describe goal",
            "status" : "Not started"
        }
        if len(self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.goal)) == 1:
            activities["goal"]["status"] = "Started"

        activities["context"] = {
            "link" : "/context_model_request?endpoint=edit_context_dialogue",
            "name" : "Describe context",
            "status" : "Not started"}   
        if len(self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.context)) == 1:
            activities["context"]["status"] = "Started"
            
        activities["alternatives"] = {
            "link" : "/add_alternative_dialogue",
            "name" : "Add alternatives",
            "status" : "Not started"}
        alternatives_number = len(self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.alternative))
        if alternatives_number > 0:
            activities["alternatives"]["status"] = "Started"


        activities["properties"] = {
            "link" : "/property_model_request?endpoint=properties_overview_dialogue",
            "name" : "Set properties",
            "status" : "Not started"}   
        if alternatives_number == 0:
            activities["properties"]["status"] = "Unavailable"
        elif len(self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.property)) >= 1:
            activities["properties"]["status"] = "Started"

        activities["tradeoff"] = {
            "link" : "/change_decision_process_dialogue",
            "name" : "Trade-off analysis",
            "status" : "Not started"}  
        if alternatives_number < 2:
            activities["tradeoff"]["status"] = "Unavailable"
        elif len(self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.selected_trade_off_method)) == 1:
            activities["tradeoff"]["status"] = "Started"

        activities["close"] = {
            "link" : "/close_case_dialogue",
            "name" : "Decide and close case",
            "status" : "Not started"}
        if self.case_db_proxy.get_value(**db_infos, subject=case_id, predicate=orion_ns.close, object_=None, any_=False):
            activities["close"]["status"] = "Started"

        case_title = self.case_db_proxy.get_value(**db_infos, subject=case_id, predicate=orion_ns.title, object_=None, any_=False)
        if activities["close"]["status"] == "Started":
            status = "Closed"
        else:
            status = "Open"
        
        dialogue = render_template("case_status_dialogue.html", activities=activities, case_title=case_title, status=status)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/change_decision_process_dialogue", ["GET"], "text/html")
    def change_decision_process_dialogue_transition(self):
        services = []
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        
        selected_decision_process = self.case_db_proxy.get_selected_trade_off_method(user_id = user_id, user_token = user_token, case_id = case_id)

        for d in self.service_directory_proxies:
            services += d.get_services(service_type = "decision_process")
        
        dialogue = render_template("change_decision_process_dialogue.html", decision_processes = services, 
                                   selected_decision_process = selected_decision_process)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def get_ontology_instances(self, class_name = None, class_name_list = None, returned_information= (0, 1, 2, 3)):
        """
        Returns a list containing all the instances of the given class in the ontology.
        The result is a list of list, where the inner list elements are the instances' uri, gradeID, title, and description.
        The outer list is sorted according to gradeId.
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
            query_result = self.get_ontology().query(q, initNs = { "orion": orion_ns }, 
                                                     initBindings = { "?class_name": rdflib.URIRef(class_name) })
            class_result = []
            for line in query_result:
                class_result.append([line[index].toPython() for index in returned_information])
            result += class_result
            
        return result

    
    @endpoint("/add_stakeholder_dialogue", ["GET"], "text/html")
    def add_stakeholder_dialogue_transition(self):
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        
        # Define the relevant ontology namespaces
        orion_ns = rdflib.Namespace(self.orion_ns)
        user_ns = rdflib.Namespace(self.authentication_service_proxy.get_user_namespace())
        
        # Get the uris of the users who are currently stakeholders in the case
        case_users = self.case_db_proxy.case_users(user_id=user_id, user_token=user_token, case_id=case_id)
        user_ids = self.case_db_proxy.user_ids(user_id=user_id, user_token=user_token)

        # Separate all existing users into those that are in the case, and those that are not. 
        # Create a list of each, consisting of (user name, uri).
        current_users = [(self.authentication_service_proxy.get_user_name(user_id=u), str(user_ns[u]))
                         for u in user_ids if str(user_ns[u]) in case_users]
        new_users = [(self.authentication_service_proxy.get_user_name(user_id=u), str(user_ns[u]))
                     for u in user_ids if str(user_ns[u]) not in case_users]
        
        # From the ontology, get all the options for orion:RoleType, orion:RoleFunction, orion:RoleLevel and orion:RoleTitle.
        # The lists include tuples with uri, gradeId, title, description.

        # Get the different categories of roles from the ontology, excluding orion:person..
        q = """\
        SELECT ?role_property ?role_class ?role_title
        WHERE {
            ?role_property a owl:ObjectProperty .
            ?role_property rdfs:domain orion:Role .
            ?role_property rdfs:range ?role_class .
            ?role_class  orion:title ?role_title .
            FILTER (?role_property != orion:person)
        }
        ORDER BY ?role_title
        """
        role_categories = self.get_ontology().query(q, initNs = { "orion": orion_ns, "owl": rdflib.OWL })
        role_categories = [(rc[0].toPython(), rc[1].toPython(), rc[2].toPython().lower().replace(" ", "_")) for rc in role_categories]
        
        
        role_properties = [role_property for (role_property, _, _) in role_categories]
        current_roles_dictionary = self.case_db_proxy.get_stakeholder(user_id=user_id, user_token=user_token, case_id=case_id,
                                                                      role_properties_list=role_properties)

        # Column labels consist of the role category title and uri
        column_labels = [(rc[2], rc[0]) for rc in role_categories]
        
        # Possible column values consists of a mapping from column label uri to a list of option title and uri
        possible_column_values = dict()
        for (role_property, role_class, _) in role_categories:
            values = [(rv[2], rv[0]) for rv in self.get_ontology_instances(role_class)]
            possible_column_values[role_property] = values
            
        # Render the dialogue
        dialogue = render_template("add_stakeholder_dialogue.html", new_users=new_users, row_labels=current_users, column_labels=column_labels,
                                   possible_column_values=possible_column_values, current_cell_values=current_roles_dictionary)
        return self.main_menu_transition(main_dialogue=dialogue)
    
    @endpoint("/add_stakeholder", ["POST", "GET"], "text/html")
    def add_stakeholder(self, stakeholder):
        """
        Adds a Stakeholder relationship between the current case and the user given as argument, with the role contributor.
        """
        self.case_db_proxy.add_stakeholder(user_id=session["user_id"], user_token=session["user_token"], case_id=session["case_id"], 
                                           stakeholder=stakeholder)
        return self.main_menu_transition(main_dialogue = "Stakeholder added!")

    @endpoint("/change_stakeholder_role", ["POST", "GET"], "text/html")
    def change_stakeholder_role(self, role_property, stakeholder):
        """
        Changes a role property of a stakeholder.
        """
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        
        try:
            values_list = dict(request.form)["select_" + role_property + "_" + stakeholder]
        except KeyError:
            values_list = []
            
        self.case_db_proxy.change_stakeholder(user_id=user_id, user_token=user_token, case_id=case_id, role_property=role_property,
                                              stakeholder=stakeholder, values_list=values_list)
        return self.add_stakeholder_dialogue_transition()

    @endpoint("/add_alternative_dialogue", ["GET"], "text/html")
    def add_alternative_dialogue_transition(self):
        orion_ns = rdflib.Namespace(self.orion_ns)
        asset_usage_list = self.get_ontology_instances(orion_ns.AssetUsage, returned_information=[0, 2])
        
        origin_options_list = self.get_ontology_instances(class_name_list=(orion_ns.ExternalOriginOption, orion_ns.InternalOriginOption),
                                                          returned_information=[0, 1, 2])
        origin_options_list = [[e[0], e[2]] for e in origin_options_list if e[1].startswith("AO")] #Open source is both a Origin option and a sub option.
        
        types_list = self.get_ontology_instances(class_name_list=(orion_ns.HardwareElement, orion_ns.InformationElement, 
                                                                  orion_ns.ServiceElement, orion_ns.SoftwareElement, orion_ns.SystemElement),
                                                 returned_information=[0, 2])
        
        dialogue = render_template("add_alternative_dialogue.html", asset_usage_list=asset_usage_list, origin_options_list=origin_options_list,
                                   types_list=types_list)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/edit_case_description_dialogue", ["GET"], "text/html")    
    def edit_case_description_dialogue_transition(self):
        result = self.case_db_proxy.get_case_description(user_id = session["user_id"], user_token = session["user_token"], case_id = session["case_id"])
        dialogue = render_template("edit_case_description_dialogue.html", title = result[0], description = result[1])
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/login_user", ["POST"], "text/html")
    def login_user(self, user_id, password):
        """
        Endpoint representing the transition from the initial dialogue to the main menu.
        """
        if user_id == "" or password == "":
            # If user_id or password is missing, show the dialogue again with an error message
            return render_template("initial_dialogue.html", error = "FieldMissing")
        elif not self.authentication_service_proxy.user_exists(user_id = user_id):
            # If user_id does not exist, show the dialogue again with an error message
            return render_template("initial_dialogue.html", error = "WrongPasswordOrUser")
        else:
            # User exists, check if the password is correct (in which case a user token string is received
            user_token = self.authentication_service_proxy.check_user_password(user_id = user_id, password = password)
            if user_token:
                # Login successful, save some data in the session object, and go to main menu
                session["user_id"] = user_id
                session["user_token"] = user_token

                # To make sure that the cache is cleared and no case is selected, delete cookie information about case id.
                session.pop("case_id", None)

                # Add the user to the case db if it is not already there
                return self.main_menu_transition()
            else:
                # If the wrong password was entered, show the dialogue again with an error message
                return render_template("initial_dialogue.html", error = "WrongPasswordOrUser")


    @endpoint("/create_user", ["POST"], "text/html")
    def create_user(self, user_id, password1, password2, name, email):
        """
        Endpoint representing the transition from the create user dialogue to the main menu.
        If the user exists, it returns to the create user dialogue and displays a message about this.
        As a transition action, it creates the new user in the database.
        """
        # TODO: Show the correct values pre-filled when the dialogue is reopened. 
        if self.authentication_service_proxy.user_exists(user_id = user_id):
            # If the user already exists, go back to the create user dialogue, with a message
            return render_template("create_user_dialogue.html", error = "UserExists")
        elif password1 != password2:
            return render_template("create_user_dialogue.html", error = "PasswordsNotEqual")
        else:
            # Otherwise, create the user in the database, and return to the initial dialogue.
            try:
                self.authentication_service_proxy.create_user(user_id = user_id, password = password1, email = email, name = name)
            except Exception as e:
                self.ms.logger.error("Failed to create user")
                self.ms.logger.error("Exception: " + str(e))
            return render_template("initial_dialogue.html")


    @endpoint("/create_case", ["POST"], "text/html")
    def create_case(self, title, description):
        """
        Endpoint representing the transition from the create case dialogue to the main menu.
        As a transition action, it creates the new case in the database, and connects the current user to it.
        """
        session["case_id"] = self.case_db_proxy.create_case(user_id = session["user_id"], user_token = session["user_token"], title = title, description = description)
        return self.case_status_dialogue_transition(), 


    @endpoint("/load_case", ["GET"], "text/html")
    def load_case(self, case_id):
        # TODO: Instead of showing case id on screen, it should be the case name + id
        session["case_id"] = case_id
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": case_id}
        
        if not self.case_db_proxy.is_case_in_database(**db_infos):
            case_graph_description = self.knowledge_repository_proxy.import_case(case_uri=case_id, format_="n3")
            self.case_db_proxy.import_case(**db_infos, graph_description=case_graph_description, format_="n3")
        
        return self.case_status_dialogue_transition()
    
    @endpoint("/close_case_dialogue", ["GET"], "text/html")
    def close_case_dialogue(self):
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        user_id = db_infos["user_id"]
        user_token=db_infos["user_token"]
        case_id = db_infos["case_id"]
        
        selected_alternative_uri = self.case_db_proxy.get_value(**db_infos, subject=case_id, predicate=orion_ns.selected_alternative, 
                                                                object_=None, default_value=None, any_=False)
        comments = self.case_db_proxy.get_value(**db_infos, subject=case_id, predicate=orion_ns.comments, object_=None, default_value="", 
                                                any_=False)
        alternative_list = self.case_db_proxy.get_decision_alternatives(user_id=user_id, token=user_token, case_id=case_id)
        dialogue = render_template("close_case_dialogue.html", selected_alternative=selected_alternative_uri, comments=comments,
                                   alternative_list=alternative_list)
        return self.main_menu_transition(main_dialogue = dialogue)
    
    @endpoint("/close_case", ["POST"], "text/html")
    def close_case(self, selected_alternative, comments, export_to_kr_checkbox=""):
        submit_component = request.values.to_dict()["submit_component"]
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        
        if submit_component == "Delete case":
            self.case_db_proxy.remove_case(**db_infos)
            dialogue = "Case deleted"
        else:
            if selected_alternative == "None":
                selected_alternative = None
            self.case_db_proxy.add_case_decision(**db_infos, selected_alternative_uri=selected_alternative, comments=comments)
            self.case_db_proxy.close_case(**db_infos)
            
            if export_to_kr_checkbox == "on":
                description = self.case_db_proxy.export_case_data(**db_infos, format_="n3")
                self.knowledge_repository_proxy.export_case(graph_description=description, format_="n3")
            dialogue = "Case closed"
            
        del session["case_id"]
        return self.main_menu_transition(main_dialogue=dialogue)
    
    @endpoint("/open_case", ["GET"], "text/html")
    def open_case(self):
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        self.case_db_proxy.open_case(**db_infos)
        return self.main_menu_transition(main_dialogue="Case opened")
    
    @endpoint("/compute_similarity_dialogue", ["GET"], "text/html")
    def compute_similarity_dialogue(self):
        return self.main_menu_transition(main_dialogue=render_template("compute_similarity_dialogue.html"))
    
    
    @endpoint("/compute_similarity", ["POST"], "text/html")
    def compute_similarity(self, number_of_returned_case, number_ratio_threshold, goal_weight, context_weight, stakeholders_weight):
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_uri": session["case_id"]}
        case_db = self.get_setting("database")
        
        number_of_returned_case = int(number_of_returned_case)
        number_ratio_threshold = float(number_ratio_threshold)
        goal_weight = int(goal_weight)
        context_weight = int(context_weight)
        stakeholders_weight = int(stakeholders_weight)
        similar_cases = self.knowledge_repository_proxy.get_similar_cases(**db_infos, case_db=case_db, 
                                                                          number_of_returned_case=number_of_returned_case,
                                                                          number_ratio_threshold=number_ratio_threshold, 
                                                                          goal_weight=goal_weight, context_weight=context_weight,
                                                                          stakeholders_weight=stakeholders_weight)
        
        return self.main_menu_transition(main_dialogue=render_template("computed_similarity.html", similar_cases_list=similar_cases))


    @endpoint("/logout", ["GET"], "text/html")
    def logout(self):
        """
        Endpoint representing the transition to the logged out state, which is the same as the initial state.
        The user id, user token and case id are deleted from the session.
        """
        try:
            self.authentication_service_proxy.logout_user(user_id = session.pop("user_id"), user_token = session.pop("user_token"))
            session.pop("user_id", None)
            session.pop("user_token", None)
            session.pop("case_id", None)
        except KeyError:
            # If the user is already logged out, the user_id, user_token, and case_id is no longer available.
            pass
        return render_template("initial_dialogue.html")

    
    @endpoint("/change_password_dialogue", ["GET"], "text/html")
    def change_password_dialogue_transition(self):
        dialogue = render_template("change_password_dialogue.html")
        return self.main_menu_transition(main_dialogue = dialogue)


    @endpoint("/change_password", ["POST"], "text/html")
    def change_password(self, password1, password2):
        if password1 == password2:
            self.authentication_service_proxy.change_password(user_id = session["user_id"], user_token = session["user_token"], password = password1)
            return self.main_menu_transition(main_dialogue = "Password changed!")
        else:
            return render_template("change_password_dialogue.html", error = "PasswordsNotEqual")
        

    @endpoint("/user_profile_dialogue", ["GET"], "text/html")
    def user_profile_dialogue_transition(self):
        # Create links to the user's profile
        user_profile = {'user_name': self.authentication_service_proxy.get_user_name(user_id = session["user_id"]),
                        'email': self.authentication_service_proxy.get_user_email(user_id = session["user_id"]),
                        'company_name': self.authentication_service_proxy.get_company_name(user_id = session["user_id"]),
                        'skype_id': self.authentication_service_proxy.get_skype_id(user_id = session["user_id"]),
                        'user_phone': self.authentication_service_proxy.get_user_phone(user_id = session["user_id"]),
                        'location': self.authentication_service_proxy.get_user_location(user_id = session["user_id"]),
                        'user_bio': self.authentication_service_proxy.get_user_bio(user_id = session["user_id"])}
        dialogue = render_template("user_profile_dialogue.html", user_profile = user_profile)
        return self.main_menu_transition(main_dialogue = dialogue)

    @endpoint("/edit_user_profile", ["POST"], "text/html")
    def edit_user_profile(self, user_name, company_name, email, skype_id, user_phone, location, user_bio):
        self.authentication_service_proxy.set_user_profile(user_id = session["user_id"], user_token = session["user_token"], user_name = user_name, 
                                                           company_name = company_name, email = email, skype_id = skype_id, user_phone = user_phone,
                                                           location = location, user_bio = user_bio)
        return self.main_menu_transition(main_dialogue = "User profile details changed!")
        
    @endpoint("/change_case_description", ["POST"], "text/html")
    def change_case_description(self, title, description):
        self.case_db_proxy.change_case_description(user_id = session["user_id"], user_token = session["user_token"], case_id = session["case_id"], title = title, description = description)
        return self.main_menu_transition(main_dialogue = "Case description changed!")


    @endpoint("/change_decision_process", ["POST"], "text/html")
    def change_decision_process(self, url):
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        
        self.case_db_proxy.change_selected_trade_off_method(user_id = user_id, user_token = user_token, case_id = case_id, microservice_url = url)
        return self.main_menu_transition(main_dialogue = "Decision process changed!")


    @endpoint("/add_alternative", ["POST"], "text/html")
    def add_alternative(self, title, description, asset_usage, asset_origin):
        """
        Adds a new decision alternative and adds a relation from the case to the alternative.
        """
        try:
            asset_type_list = dict(request.form)["asset_type"]
        except KeyError:
            asset_type_list = []
        
        asset_characteristics = [("asset_type", asset_type) for asset_type in asset_type_list]
        if asset_usage != "Unknown":
            asset_characteristics.append(("asset_usage", asset_usage))
        if asset_origin != "Unknown":
            asset_characteristics.append(("asset_origin", asset_origin))
            
        self.case_db_proxy.add_alternative(user_id=session["user_id"], user_token=session["user_token"], case_id=session["case_id"], 
                                           title=title, description=description, asset_characteristics=asset_characteristics)
        return self.main_menu_transition(main_dialogue = "New alternative added!")


    @endpoint("/export_case_to_knowledge_repository", ["GET"], "text/html")
    def export_case_to_knowledge_repository(self):
        """
        Exports the current case to the knowledge repository.
        """
        user_id = session["user_id"]
        user_token = session["user_token"]
        case_id = session["case_id"]
        description = self.case_db_proxy.export_case_data(user_id = user_id, user_token = user_token, case_id = case_id, format_ = "n3")
        print(description)
        self.knowledge_repository_proxy.export_case(graph_description=description, format_="n3")
        
        description = description.replace("&", "&amp;")
        description = description.replace("<", "&lt;")
        description = description.replace(">", "&gt;")
        message = "Exported case to knowledge repository, with the following data:\n\n"
        message += '<div style="white-space: pre-wrap;"><code>' + description + "</code></div>"
        return self.main_menu_transition(main_dialogue = message)
        

    @endpoint("/get_service_directories", ["GET"], "text/html")
    def get_service_directories(self):
        """
        Returns the list of service directories registered with this service as a json file.
        """
        return json.dumps(self.get_setting("service_directories"))


    @endpoint("/show_ontology", ["GET", "POST"], "text/html")
    def show_ontology(self, format):
        """
        Shows the base OWL ontology used by the core services in the service specified by the format parameter.
        """
        description = self.case_db_proxy.get_ontology(format = format)
        description = description.replace("&", "&amp;")
        description = description.replace("<", "&lt;")
        description = description.replace(">", "&gt;")
        message = "Exported case to knowledge repository, with the following data:\n\n"
        message += '<div style="white-space: pre-wrap;"><code>' + description + '<code></div>'
        return self.main_menu_transition(main_dialogue = message)
    

    @endpoint("/edit_goal_description_dialogue", ["GET", "POST"], "text/html")
    def edit_goal_description_dialogue(self):
        """
        Transition to the dialogue for providing a textual description for a goal. 
        """
        case_id = session["case_id"]
        orion_ns = rdflib.Namespace(self.orion_ns)
        description = ""

        # If a goal exists, fetch its description
        goals = self.case_db_proxy.get_objects(user_id=session["user_id"], user_token=session["user_token"],
                                               case_id=case_id, subject=case_id, predicate=orion_ns.goal)
        if goals:
            goal_uri = goals[0]
            descriptions = self.case_db_proxy.get_objects(user_id=session["user_id"], user_token=session["user_token"],
                                                          case_id=case_id,
                                                          subject=goal_uri, predicate=orion_ns.description)
            if descriptions:
                description = descriptions[0]

        dialogue = render_template("edit_goal_description_dialogue.html", description = description)
        return self.main_menu_transition(main_dialogue = dialogue)


    @endpoint("/change_goal_description", ["POST"], "text/html")
    def change_goal_description(self, description):
        """
        Update the goal description with a new text.
        """
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        case_id = db_infos["case_id"]
        orion_ns = rdflib.Namespace(self.orion_ns)

        # Does the case already have a Goal element? If not, create it, and bind its url to goal_url.
        goals = self.case_db_proxy.get_objects(**db_infos, subject=case_id, predicate=orion_ns.goal)
        if goals:
            goal_uri = goals[0]
        else:
            goal_uri = self.case_db_proxy.add_resource(**db_infos, resource_class="Goal")
            self.case_db_proxy.add_object_property(**db_infos, resource1=case_id, property_name=orion_ns.goal, resource2=goal_uri)

        # Add the description
        self.case_db_proxy.add_datatype_property(**db_infos, resource = goal_uri, property_name = orion_ns.description, 
                                                 value = rdflib.Literal(description))
        return self.main_menu_transition(main_dialogue = "Goal description changed!")


    @endpoint("/goal_dialogue_transition", ["GET", "POST"], "text/html")
    def goal_dialogue_transition(self, class_name, property_name):
        """
        Transition to the dialogue for the goal category customer value.
        Class name is a subcategory of Goal, and property name the property linking to that subcategory.
        """
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        case_id = db_infos["case_id"]
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        # Does the case already have a Goal element? If not, create it, and bind its url to goal_url.
        goals = self.case_db_proxy.get_objects(**db_infos, subject = case_id, predicate = orion_ns.goal)
        if goals:
            goal_uri = goals[0]
        else:
            goal_uri = self.case_db_proxy.add_resource(**db_infos, resource_class = "Goal")
            self.case_db_proxy.add_object_property(**db_infos, resource1 = case_id, property_name = orion_ns.goal, resource2 = goal_uri)
        
        class_title = self.get_ontology().value(orion_ns[class_name], orion_ns.title, None)

        # Which goal subcategories are selected?
        checked = self.case_db_proxy.get_objects(**db_infos, subject = goal_uri, predicate = orion_ns[property_name])

        # Instances contains all uri:s in the ontology that are linked from a subject of class class_name with the predicate property_name.
        # The gradeId, title and description are also provided. The last field indicates if the item has been selected.
        instances = [(uri.replace("#", "%23"), gradeId, title, description, str(uri) in checked) 
                     for (uri, gradeId, title, description) in 
                     self.get_ontology_instances(orion_ns[class_name])]
        
        # Render the dialogue and display it
        result = render_template("goal_dialogue.html", 
                                 class_title = class_title,
                                 instances = instances,
                                 goal_uri = goal_uri.replace("#", "%23"),
                                 class_name = class_name,
                                 property_name = property_name)
        return self.main_menu_transition(main_dialogue = result)
    
    
    @endpoint("/toggle_goal_value", ["GET", "POST"], "text/html")
    def toggle_goal_value(self, class_name, property_name, goal_uri, value_uri):
        """
        This method is called when the user ticks a checkbox in one of the goal dialogues.
        It updates the database, and then displays the goal dialogue again.
        """
        orion_ns = rdflib.Namespace(self.orion_ns)
        db_infos = {"user_id": session["user_id"], "user_token": session["user_token"], "case_id": session["case_id"]}
        self.case_db_proxy.toggle_object_property(**db_infos, resource1 = goal_uri, property_name = orion_ns[property_name], resource2 = value_uri)
        return self.goal_dialogue_transition(class_name = class_name, property_name = property_name)
    
    
    @endpoint("/github_update", ["GET", "POST"], "text/plain")
    def github_update(self):
        """
        Webservice hook for automatic update on GitHub events. When the hook is called, it triggers a shell script that
        pulls the latest commit from the GitHub directory, and then restarts Apache. 
        Only requests from github.com are accepted, and a correct signature key must be provided.
        
        The code is based on: https://github.com/razius/github-webhook-handler/blob/master/index.py, but greatly simplified.
        """
        
        # This endpoint only makes sense on servers
        if self.get_setting("mode") == "local":
            return "OK"
        
        if request.method == 'GET':
            return 'OK'
        elif request.method == 'POST':
            # Store the IP address of the requester
            request_ip = ipaddress.ip_address(u'{0}'.format(request.remote_addr))
    
            # Get the GitHub IP addresses used for hooks.
            hook_blocks = requests.get('https://api.github.com/meta').json()['hooks']
    
            # Check if the POST request is from github.com
            for block in hook_blocks:
                if ipaddress.ip_address(request_ip) in ipaddress.ip_network(block):
                    break  # the remote_addr is within the network range of github.
            else:
                abort(403)

            # GitHub may send a "ping" request to test the hook.    
            if request.headers.get('X-GitHub-Event') == "ping":
                return json.dumps({'msg': 'Hi!'})

            # All other event types than "push" and "ping" are not handled.
            if request.headers.get('X-GitHub-Event') != "push":
                return json.dumps({'msg': "wrong event type"})

            # Check that request signature matches the key
            key = self.github_key.encode()
            signature = request.headers.get('X-Hub-Signature').split('=')[1]
            mac = hmac.new(key, msg = request.data, digestmod = sha1)
            if not hmac.compare_digest(mac.hexdigest(), signature):
                abort(403)

            # Run the script that updates the code from GitHub and restarts Apache.
            try:
                output = subprocess.check_output(["sudo", "-n", "bash", self.get_setting("github_update_script")],
                                                 stderr = subprocess.STDOUT)
                return "github_update successfully executed " + self.get_setting("github_update_script") + " with the following output:\n\n" + output
            except subprocess.CalledProcessError as e:
                return "github_update failed to execute " + str(e.cmd) + " resulting in return code " + str(e.returncode) + " and the following output:\n\n" + str(e.output)
