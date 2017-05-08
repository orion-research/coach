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
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        # Setup encryption for settings cookies
        self.ms.secret_key = secret_data["secret_key"]

        # Setup key for GitHub webhook
        self.github_key = secret_data["github_key"]

        # Store authentication service connection
        self.authentication_service_proxy = self.create_proxy(self.get_setting("authentication_service"))

        # Store case database connection, using user_id and user_token as default parameters to all endpoint calls.
        self.case_db_proxy = self.create_proxy(self.get_setting("database"))

        # Store point to service directories
        self.service_directory_proxies = [self.create_proxy(sd) for sd in self.get_setting("service_directories")]

        # Placeholder for the ORION ontology. Since the ontology is loaded from the case database, it is not given a value here.
        # This is because it cannot be assumed that the case database is up and running at this point.
        # Instead, the ontology is loaded upon the first call to the method self.get_ontolog(), which should be used for accessing it.
        self.ontology = None

                            
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
            self.ontology.parse(data = self.case_db_proxy.get_ontology(format = "ttl"), format = "ttl")
        return self.ontology
        
    
    @endpoint("/", ["GET"], "text/html")
    def initial_transition(self):
        # Store the software version in the session object
        session["version"] = self.get_version()
        return render_template("initial_dialogue.html")


    @endpoint("/create_user_dialogue", ["GET"], "text/html")
    def create_user_dialogue_transition(self):
        return render_template("create_user_dialogue.html")

    
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
        decision_process = ""
        if "case_id" in session:
            try:
                decision_process = self.case_db_proxy.get_decision_process(case_id = session["case_id"])
                if decision_process:
                    decision_process_proxy = self.create_proxy(decision_process)
                    context["process_menu"] = decision_process_proxy.process_menu(case_id = session["case_id"])
            except Exception as e:
                print("Error in main_menu_transition, with decision_process = " + str(decision_process) + ": " + str(e))
        return render_template("main_menu.html", **context)


    @endpoint("/decision_process_request", ["GET", "POST"], "text/html")
    def decision_process_request(self):
        """
        Endpoint which relays a request to the decision process associated with the currently active case.
        It always passes the current decision case id as a parameter in the request.
        It requests a delegate token from the authentication server, and then revokes it after the call.
        """
        decision_process = self.case_db_proxy.get_decision_process(case_id = session["case_id"])
        delegate_token = self.authentication_service_proxy.get_delegate_token(user_id = session["user_id"], user_token = session["user_token"], 
                                                                              case_id = session["case_id"])
        if decision_process:
            params = request.values.to_dict()
            del params["endpoint"]
            params["user_id"] = session["user_id"]
            params["delegate_token"] = delegate_token
            params["case_db"] = self.get_setting("database")
            params["case_id"] = session["case_id"]
            params["directories"] = json.dumps(self.get_setting("service_directories"))
            params["knowledge_repository"] = self.get_setting("knowledge_repository")
            response = requests.request(request.method, decision_process + "/" + request.values["endpoint"], params = params)
            self.authentication_service_proxy.revoke_delegate_token(user_id = session["user_id"], user_token = session["user_token"], 
                                                                    case_id = session["case_id"])
            return self.main_menu_transition(main_dialogue = response.text)
        else:
            return "No decision process selected"
        
    
    @endpoint("/context_model_request", ["GET", "POST"], "text/html")
    def context_model_request(self):
        """
        Endpoint which relays a request to the context model.
        It always passes the current decision case database url and case id as a parameter in the request.
        """
        context_service = self.get_setting("context_service")
        delegate_token = self.authentication_service_proxy.get_delegate_token(user_id = session["user_id"], user_token = session["user_token"], 
                                                                              case_id = session["case_id"])
        params = request.values.to_dict()
        del params["endpoint"]
        params["user_id"] = session["user_id"]
        params["delegate_token"] = delegate_token
        params["case_db"] = self.get_setting("database")
        params["case_id"] = session["case_id"]
        params["knowledge_repository"] = self.get_setting("knowledge_repository")
        response = requests.request(request.method, context_service + "/" + request.values["endpoint"], 
                                    params = params)
        self.authentication_service_proxy.revoke_delegate_token(user_id = session["user_id"], user_token = session["user_token"], 
                                                                case_id = session["case_id"])
        return self.main_menu_transition(main_dialogue = response.text)
        
    
    @endpoint("/create_case_dialogue", ["GET"], "text/html")
    def create_case_dialogue_transition(self):
        dialogue = render_template("create_case_dialogue.html")
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/open_case_dialogue", ["GET"], "text/html")
    def open_case_dialogue_transition(self):
        # Create links to the user's cases
        user_cases = self.case_db_proxy.user_cases()
        links = ["<A HREF=\"/open_case?case_id=%s\">%s</A>" % tuple(pair) for pair in user_cases]

        dialogue = render_template("open_case_dialogue.html", user_cases = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/change_decision_process_dialogue", ["GET"], "text/html")
    def change_decision_process_dialogue_transition(self):
        services = []
        current_decision_process = self.case_db_proxy.get_decision_process(case_id = session["case_id"])

        for d in self.service_directory_proxies:
            services += d.get_services(service_type = "decision_process")
        options = ["<OPTION value=\"%s\" %s> %s </A>" % (s[2], "selected" if s[2] == current_decision_process else "", s[1]) for s in services]
        
        dialogue = render_template("change_decision_process_dialogue.html", decision_processes = options)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def get_ontology_instances(self, class_name, property_name, resource = None):
        """
        Returns a list containing all the instances of the given class in the ontology.
        The result is a list of tuples, where the tuple elements are the instances' uri, gradeID, title, and description,
        and a boolean indicating if there is an object property from resource by the property name in the case database.
        The list is sorted according to gradeId.
        """
        orion_ns = rdflib.Namespace("http://www.orion-research.se/ontology#")
        result = []
        for s, _, _ in self.get_ontology().triples( (None,  rdflib.RDF.type, orion_ns[class_name]) ):
            tup = (str(s),  # The URI
                   self.get_ontology().value(s, orion_ns.gradeId, None), 
                   self.get_ontology().value(s, orion_ns.title, None),
                   self.get_ontology().value(s, orion_ns.description, None))
            if resource:
                tup += (str(s) in self.case_db_proxy.get_object_properties(resource = resource, property_name = property_name), )
            result += [tup]

        # Sort the items according to gradeId
        result.sort(key = lambda p: p[1])
        return result
    
    
    @endpoint("/add_stakeholder_dialogue", ["GET"], "text/html")
    def add_stakeholder_dialogue_transition(self):

        # Get the users who are currently stakeholders in the case
        case_users = self.case_db_proxy.case_users(case_id = session["case_id"])

        # Get all users who exist both in the authentication list and in the case DB but are not stakeholders already
        user_ids = [u for u in self.case_db_proxy.user_ids() 
                    if self.authentication_service_proxy.user_exists(user_id = u)]
        current_users = [(u, self.authentication_service_proxy.get_user_name(user_id = u)) for u in user_ids if u in case_users]
        new_users = [(u, self.authentication_service_proxy.get_user_name(user_id = u)) for u in user_ids if u not in case_users]

        # Define the relevant ontology namespaces
        orion_ns = rdflib.Namespace("http://www.orion-research.se/ontology#")
        data_ns = rdflib.Namespace(self.case_db_proxy.get_data_namespace())
        case_uri = data_ns[str(session["case_id"])]
        
        # From the ontology, get all the options for orion:RoleType, orion:RoleFunction, orion:RoleLevel and orion:RoleTitle.
        # The lists include tuples with uri, gradeId, title, description.
        role_values = dict()
        role_values["roleType"] = self.get_ontology_instances("RoleType", "roleType")
        role_values["roleFunction"] = self.get_ontology_instances("RoleFunction", "roleFunction")
        role_values["roleLevel"] = self.get_ontology_instances("RoleLevel", "roleLevel")
        role_values["roleTitle"] = self.get_ontology_instances("RoleTitle", "roleTitle")
        
        # Create the entries in the matrix, based on the selected value for each property and person
        # Get all the role nodes linked to the case node with case_id.
        roles = self.case_db_proxy.get_object_properties(resource = case_uri, property_name = "role")
        # For each role node, go through all the properties
        role_properties = dict()
        for role in roles:
            # Find the person of the role and get the user_id
            person = self.case_db_proxy.get_object_properties(resource = role, property_name = "person")[0]
            person_user_id = self.case_db_proxy.get_datatype_property(resource = person, property_name = "user_id")
            # Create a matrix where for each person and property name, the selected property value (if any) is stored
            role_properties[person_user_id] = dict()
            for property_name in role_values.keys():
                # The matrix value is a list of uri:s, where an empty list means that no value was found
                role_properties[person_user_id][property_name] = self.case_db_proxy.get_object_properties(resource = role, property_name = property_name)
         
        # Render the dialogue
        dialogue = render_template("add_stakeholder_dialogue.html", current_users = current_users, new_users = new_users,
                                   role_values = role_values, role_properties = role_properties)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/add_stakeholder", ["POST", "GET"], "text/html")
    def add_stakeholder(self, stakeholder):
        """
        Adds a Stakeholder relationship between the current case and the user given as argument, with the role contributor.
        """
        self.case_db_proxy.add_stakeholder(case_id = session["case_id"], stakeholder = stakeholder, role = "contributor")
        return self.main_menu_transition(main_dialogue = "Stakeholder added!")


    @endpoint("/change_stakeholder_role", ["POST", "GET"], "text/plain")
    def change_stakeholder_role(self, property, stakeholder, value):
        """
        Changes a role property of a stakeholder.
        """
        # Define the relevant ontology namespaces
        orion_ns = rdflib.Namespace("http://www.orion-research.se/ontology#")
        data_ns = rdflib.Namespace(self.case_db_proxy.get_data_namespace())
        case_uri = data_ns[str(session["case_id"])]

        # Find the appropriate role node for the case_id and stakeholder.
        # Get all the role nodes linked to the case node with case_id.
        roles = self.case_db_proxy.get_object_properties(resource = case_uri, property_name = "role")
        # Now filter the list of roles for nodes which are linked to a person with the right id
        for r in roles:
            person = self.case_db_proxy.get_object_properties(resource = r, property_name = "person")[0]
            user_id = self.case_db_proxy.get_datatype_property(resource = person, property_name = "user_id")
            if user_id == stakeholder:
                # Right role found, so remove previous property values and add the new one
                previous_values = self.case_db_proxy.get_object_properties(resource = r, property_name = property)
                for p in previous_values:
                    self.case_db_proxy.remove_object_property(resource1 = r, property_name = property, resource2 = p)
                self.case_db_proxy.add_object_property(resource1 = r, property_name = property, resource2 = value)
                return "Ok"
        return "Ok"
    

    @endpoint("/add_alternative_dialogue", ["GET"], "text/html")
    def add_alternative_dialogue_transition(self):
        dialogue = render_template("add_alternative_dialogue.html")
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/edit_case_description_dialogue", ["GET"], "text/html")    
    def edit_case_description_dialogue_transition(self):
        result = self.case_db_proxy.get_case_description(case_id = session["case_id"])
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
            return render_template("initial_dialogue.html", error = "NoSuchUser")
        else:
            # User exists, check if the password is correct (in which case a user token string is received
            user_token = self.authentication_service_proxy.check_user_password(user_id = user_id, password = password)
            if user_token:
                # Login successful, save some data in the session object, and go to main menu
                session["user_id"] = user_id
                session["user_token"] = user_token
                # Add the user_id and user_token as default keyword arguments to the database proxy
                self.case_db_proxy.default_kwargs = {"user_id": user_id, "user_token": user_token}

                # Add the user to the case db if it is not already there
                self.case_db_proxy.create_user()
                return self.main_menu_transition()
            else:
                # If the wrong password was entered, show the dialogue again with an error message
                return render_template("initial_dialogue.html", error = "WrongPassword")


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
        session["case_id"] = self.case_db_proxy.create_case(title = title, description = description, initiator = session["user_id"])
        return self.main_menu_transition()


    @endpoint("/open_case", ["GET"], "text/html")
    def open_case(self, case_id):
        # TODO: Instead of showing case id on screen, it should be the case name + id
        session["case_id"] = case_id
        return self.main_menu_transition()
        

    @endpoint("/logout", ["GET"], "text/html")
    def logout(self):
        """
        Endpoint representing the transition to the logged out state, which is the same as the initial state.
        The user id and token are deleted from the session. However, the case_id is kept, so that the
        user directly returns to the case being worked on when loggin in again.
        """
        try:
            self.authentication_service_proxy.logout_user(user_id = session.pop("user_id"), user_token = session.pop("user_token"))
            session.pop("user_id", None)
            session.pop("user_token", None)
            # Remove the default keyword arguments from the case_db_proxy
            self.case_db_proxy.default_kwargs = dict()
        except:
            # If the user is already logged out, the user_id, user_token, and case_id is no longer available.
            pass
        return render_template("initial_dialogue.html")


    @endpoint("/change_password", ["GET"], "text/html")
    def change_password(self):
        return self.main_menu_transition(main_dialogue = "Not yet implemented!")


    @endpoint("/change_case_description", ["POST"], "text/html")
    def change_case_description(self, title, description):
        self.case_db_proxy.change_case_description(case_id = session["case_id"], title = title, description = description)
        return self.main_menu_transition(main_dialogue = "Case description changed!")


    @endpoint("/change_decision_process", ["POST"], "text/html")
    def change_decision_process(self, url):
        self.case_db_proxy.change_decision_process(case_id = session["case_id"], decision_process = url)
        menu = requests.get(url + "/process_menu", params = {"case_id": session["case_id"]}).text
        return self.main_menu_transition(main_dialogue = "Decision process changed!", process_menu = menu)


    @endpoint("/add_alternative", ["POST"], "text/html")
    def add_alternative(self, title, description):
        """
        Adds a new decision alternative and adds a relation from the case to the alternative.
        """
        self.case_db_proxy.add_alternative(title = title, description = description, case_id = session["case_id"])
        return self.main_menu_transition(main_dialogue = "New alternative added!")


    @endpoint("/export_case_to_knowledge_repository", ["GET"], "text/html")
    def export_case_to_knowledge_repository(self):
        """
        Exports the current case to the knowledge repository.
        """
        description = self.case_db_proxy.export_case_data(case_id = session["case_id"], format = "json")
        requests.post(self.get_setting("knowledge_repository") + "/add_case", data = {"description": json.dumps(description)})
        print(description)
        return self.main_menu_transition(main_dialogue = "Exported case to knowledge repository!")
        

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
        result = "<DIV style=\"\white-space: pre-wrap;\">" + self.case_db_proxy.get_ontology(format = format) + "</DIV>"
        return self.main_menu_transition(main_dialogue = result)
    
    
    @endpoint("/goal_dialogue_transition", ["GET", "POST"], "text/html")
    def goal_dialogue_transition(self, class_name, property_name):
        """
        Transition to the dialogue for the goal category customer value.
        """
        
        orion_ns = rdflib.Namespace("http://www.orion-research.se/ontology#")
        data_ns = rdflib.Namespace(self.case_db_proxy.get_data_namespace())
        case_uri = data_ns[str(session["case_id"])]
        
        # Does the case already have a Goal element? If not, create it, and bind its url to goal_url.
        goals = self.case_db_proxy.get_object_properties(resource = case_uri, property_name = "goal")
        if goals:
            goal_uri = goals[0]
        else:
            goal_uri = self.case_db_proxy.add_resource(resource_class = "Goal")
            self.case_db_proxy.add_object_property(resource1 = case_uri, property_name = "goal", resource2 = goal_uri)
        
        # Get all predefined resources of type CustomerValue from the ORION ontology, as a list of uri, gradeId, title, description
        # and a boolean indicating if it is currently selected or not.
        instances = self.get_ontology_instances(class_name, property_name, goal_uri)
        
        result = "".join(["<INPUT type=\"checkbox\" onclick='window.location.assign(\"/toggle_goal_value?goal_uri=" + 
                          goal_uri.replace("#", "%23") + "&value_uri=" + uri.replace("#", "%23") + 
                          "&class_name=" + class_name + "&property_name=" + property_name + "\")' " + 
                          ("checked" if checked else "") + "/>" + str(title) + "<BR>" + str(description) + "</BR>" 
                          for (uri, _, title, description, checked) in instances])
        result = "<FORM><FIELDSET><LEGEND><H2>Goal: " + self.get_ontology().value(orion_ns[class_name], orion_ns.title, None) + "</H2></LEGEND>" + result + "</FIELDSET></FORM>"
        
        return self.main_menu_transition(main_dialogue = str(result))
    
    
    @endpoint("/toggle_goal_value", ["GET", "POST"], "text/html")
    def toggle_goal_value(self, class_name, property_name, goal_uri, value_uri):
        """
        This method is called when the user ticks a checkbox in one of the goal dialogues.
        It updates the database, and then displays the goal dialogue again.
        """
        self.case_db_proxy.toggle_object_property(resource1 = goal_uri, property_name = property_name, resource2 = value_uri)
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
