"""  
Created on 16 mars 2016

@author: Jakob Axelsson

The module coach contains the framework for developing components for COACH in Python.


TODO:
Security:
- How to handle authentication and database read/write access from other services?
- Is it possible to restrict access for a client to only query on a limited set of the database? If so, this could be a way of letting 
services use general querys. Otherwise, the root must provide an API for a limited set of requests.
- The general principle for the external services is that they get access to one node in the database.
To that node they may add attributes, and they may create subnodes linked from it.
All this should happen through an API in the root service. The database itself should not be visible on the Internet.
- In the root settings, it should be possible set a regexp for what email addresses are allowed, to limit user creation.
- It is necessary to have some kind of token to ensure that access is valid after logging it. Could it be saved in the session object?
http://stackoverflow.com/questions/32510290/how-do-you-implement-token-authentication-in-flask.
For each user, a token with expiration is generated, and the token is also stored in the session object.
Whenever an endpoint requiring authentication is called, it checks if the session token is still valid.
If so, it gets a new token, and the timer is reset. If the token is no longer valid, the user is logged out.
This can all be put into one method self.authenticate(), which is called at the beginning of each endpoint.

User interface:
- Change the menu for case management. There should be one item for stakeholders, where current stakeholders can be listed and new ones added.
Also, one for alternatives, where existing ones can be shown, edited or deleted, and new ones added.
- It should be possible to change passwords!

Design:
- Make proper schemas for the case database. Estimate and EstimationMethod should be their own nodes. Maybe also property?
- Should the role of a user be part of the relation between user and decision case? Each user can have different role in different cases.
- Put the framework in this module, and create separate modules for each concrete method/process

Services:
- Develop decision processes for AHP and Pugh.

Development:
- Add logging. All transitions should be logged, and should include data from the session object. Errors should also be logged,
and possibly be alerted through email when in production. See http://flask.pocoo.org/docs/0.10/errorhandling/.
"""

# Standard libraries
from hashlib import sha1
import hmac
from inspect import getmro
import ipaddress
import json
import logging
import os
import subprocess
import threading

# Coach modules
from COACH.framework.authentication import Authentication
from COACH.framework.casedb import CaseDatabase

# Web server framework
from flask import Flask, Response, request, session, abort
from flask.views import View
from flask.templating import render_template

import requests


import inspect


# Auxiliary functions
        
def endpoint(url_path, http_methods):
    """
    endpoint is intended to be used as a decorator for the methods of a service class that should be used
    as endpoints. The function takes two arguments, a url path and a list of methods to be used with it.
    These arguments are added as attributes to the decorated method. This attributes are inspected by
    the create_endpoints method, and used to set up the method as an appropriate flask endpoint.

    Instead of just returning a function, a callable class is created. This is because Flask seems to 
    require that all endpoints are implemented by different function objects.
    """

    def decorator(f):
        f.url_path = url_path
        f.http_methods = http_methods
        return f
    
    return decorator


def get_service(url, endpoint, **kwargs):
    """
    get_service is a convenience function for calling a microservice using the http method get.
    The result of the service is returned as text. 
    """
    return requests.get(url + "/"  + endpoint, params = kwargs).text


def post_service(url, endpoint, **kwargs):
    """
    post_service is a convenience function for calling a microservice using the http method post.
    No result is returned.
    """
    requests.post(url + "/"  + endpoint, data = kwargs)


class Microservice:
    
    """
    Microservice is the base class of all microservices. It contains the functionality for setting up a service that can act as a stand-alone web server.
    It expects subclasses to implement the createEndpoints() function, which defines the service API.
    """
    
    def __init__(self, settings_file_name, handling_class = None, working_directory = None):
        """
        Initialize the microservice.
        """
        
        if working_directory:
            self.working_directory = working_directory
        else:
            self.working_directory = os.getcwd()
        
        self.handling_class = handling_class

        # Read settings from settings_file_name
        self.load_settings(settings_file_name)

        self.name = self.get_setting("name")
        self.host = self.get_setting("host")
        self.port = self.get_setting("port")

        # Create the microservice
        self.ms = Flask(self.name)
        self.ms.root_path = working_directory
        
        # If a log file name is provided, enable logging to that file
        if "logfile" in self.settings:
            handler = logging.FileHandler(self.get_setting("logfile"))
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.ms.logger.addHandler(handler)
            self.ms.logger.warning("Logging started")

        # Initialize the endpoints, as defined in concrete subclasses
        self.create_endpoints()
            

    def load_settings(self, settings_file_name):
        """
        Loads settings from a file.
        """
        with open(os.path.join(self.working_directory, os.path.normpath(settings_file_name)), "r") as file:
            fileData = file.read()
        self.settings = json.loads(fileData)


    def get_setting(self, key):
        """
        Returns the settings value for the provided key, or an exception if it does not exist.
        The settings file should be organized as a dictionary, where each entry has a class name as a key,
        and another dictionary as its value.
        The settings for a particular object is found by looking up the first class name in its class hierarchy,
        that contains the key in its dictionary. 
        If the MicroService has a handling class, this class's name is used first.
        """
        # Get the list of parent classes in method resolution order.
        if self.handling_class:
            parents = [self.handling_class.__name__] + [cls.__name__ for cls in getmro(self.__class__)]
        else:
            parents = [cls.__name__ for cls in getmro(self.__class__)]
        # Look for the key in each parent's dictionary, and return the first found.
        for p in parents:
            try:
                return self.settings[p][key]
            except:
                pass
        # If the key is not defined for any specific class, look if it is defined on the global level.
        return self.settings[key]


    def run(self):
        """
        Starts the MicroService.
        """
        
        # Depending on the server mode, start the app in different ways
        if self.get_setting("mode") == "local":
            # Run using Flask built in server with debugging on

            # Start the microservice in a separate thread, since the call does not return otherwise.
            # Also, use threaded=True, to allow the microservice to handle multiple requests.
            # To be able to run the debug mode, it is necessary to turn off the automatic reloading.
            self.thread = threading.Thread(target = self.ms.run, kwargs = {"host": self.host, "port": self.port, "use_reloader": False, "threaded": True, "debug": True})
            self.thread.start()
        elif self.get_setting("mode") in ["development", "production"]:
            self.thread = threading.Thread(target = self.ms.run, kwargs = {"host": self.host, "port": self.port, "use_reloader": False, "threaded": True, "debug": True})
            self.thread.start()
        else:
            self.ms.logger.error("Unknown server mode: " + self.get_setting("mode"))
            

    def create_endpoints(self):
        """
        create_endpoints is used by the __init__ method to define the API of the microservice.
        It automatically creates endpoints for methods decorated with the @endpoint decorator.
        Override this method in subclasses to add service endpoints manually.
        """
        # Get a list of all methods for this class.
        print("Creating endpoints for " + self.__class__.__name__ + "(" + self.host + ":" + str(self.port) + ")")
        for (_, m) in inspect.getmembers(self):
            # All endpoint methods are given the attribute url_path by the @endpoint decorator, which contains the url path,
            # and the attribute http_methods, which contains a list of the http methods that it can be used with.
            if hasattr(m, "url_path"):
                self.ms.add_url_rule(m.url_path, view_func = self.endpoint_wrapper(m), endpoint = m.__name__,
                                     methods = m.http_methods)
                print("   - " + m.__name__ + " created")


    # Class variables trace and trace_indent are used to control console trace output from endpoint calls. 
    trace = True
    trace_indent = 0

    def endpoint_wrapper(self, m):
        
        def wrapping():
            """
            The endpoint wrapping fetches the request values supplied for each of the method's parameter names
            and adds them as arguments to the method. Trace output to the console can be obtained by setting
            the class variable trace to True.
            """
            args = [request.values[p.name] for (_, p) in inspect.signature(m).parameters.items()]
            if self.trace: 
                print(self.trace_indent * "    " + m.__name__ + "(" + ", ".join(args) + ")")
                self.trace_indent += 1
            result = m(*args)
            if self.trace: 
                self.trace_indent -= 1
                print(self.trace_indent * "    " + "result from " + m.__name__ + ": " + (str(result).split("\n", 1)[0]))
            return result
        
        return wrapping
    
    
    @endpoint("/test_ui", ["GET", "POST"])
    def test_ui(self):
        """
        Returns an automatically generated html page which allows testing of individual endpoints manually through 
        a web browser.
        """
        result = "<HTML>\n<H1>Endpoints of the microservice " + type(self).__name__ + "</H1>\n"
        result += "<P>NOTE: references to services should include the protocol and a trailing / (e.g. http://127.0.0.1:5002/)</P>"
        for (_, m) in inspect.getmembers(self):
            if hasattr(m, "url_path"):
                result += "<FORM action=\"" + m.url_path + "\""
                result += " method=\"" + m.http_methods[0] + "\">\n"
                result += "<FIELDSET>\n"
                result += "<LEGEND><H2>" + m.url_path + "</H2></LEGEND>\n"
                result += "<H3>HTTP method(s):</H3>" + ", ".join(m.http_methods) + "<BR>\n"
                if m.__doc__:
                    result += "<H3>Description:</H3>\n" + m.__doc__ + "<BR><BR>\n"
                else:
                    result += "<H3>Description:</H3>\nDescription missing<BR><BR>\n"
                for (_, p) in inspect.signature(m).parameters.items():
                    result += p.name + ": <BR>\n"
                    result += "<INPUT TYPE=\"text\" name=\"" + p.name + "\"><BR>\n"
                result += "<INPUT type=\"submit\" value=\"Submit\">\n"
                result += "</FIELDSET>\n\n</FORM>\n\n\n"
        result += "</HTML>"
        return result
    
    
class RootService(Microservice):
    
    """
    RootService implements the overall workflow manager and decision case manager. It is configured with links to 
    a number of directories, which are used for searching for other services. It contains the basic
    functionality for logging in, registering users, creating and closing decision cases, attaching
    users to a decision case, and selecting the decision process. Every installation of COACH has exactly one instance of this class.
    """
    
    def __init__(self, settings_file_name, secret_data_file_name, handling_class = None, working_directory = None):
        """
        Initialize the RootService object. The secret_args argument should be a list of three strings:
        1. The database user name.
        2. The database password.
        3. The session encryption key.
        These are kept outside the settings file to ensure that they do not spread when files are shared in a repository.
        """
        
        super().__init__(settings_file_name, handling_class = handling_class, working_directory = working_directory)

        # Read secret data file
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        # Setup encryption for settings cookies
        self.ms.secret_key = secret_data["secret_key"]

        # Setup key for GitHub webhook
        self.github_key = secret_data["github_key"]

        # Initialize the user database
        self.get_setting("email")["password"] = secret_data["email_password"]
        self.root_service_url = self.get_setting("protocol") + "://" + self.get_setting("host") + ":" + str(self.get_setting("port"))
        self.authentication = Authentication(os.path.join(self.working_directory, self.get_setting("authentication_database")),
                                             self.get_setting("email"), self.root_service_url, secret_data["password_hash_salt"])

        # Initialize the case database
        try:
            self.caseDB = CaseDatabase(self.get_setting("database"), 
                                       secret_data["neo4j_user_name"], 
                                       secret_data["neo4j_password"],
                                       "CaseDB")
            self.ms.logger.info("Case database successfully connected")
        except:
            self.ms.logger.error("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")

        # Store point to service directories
        self.service_directories = self.get_setting("service_directories")
                        
    
    def get_version(self):
        """
        Returns the version of the software running. It fetches this information from git.
        """
        try:
            return subprocess.check_output(["git", "describe", "--all", "--long"], cwd = self.working_directory).decode("ascii")[-7:]
        except:
            return "No version information available"

    
    @endpoint("/", ["GET"])
    def initial_transition(self):
        # Store the software version in the session object
        session["version"] = self.get_version()
        return render_template("initial_dialogue.html")


    @endpoint("/create_user_dialogue", ["GET"])
    def create_user_dialogue_transition(self):
        return render_template("create_user_dialogue.html")

    
    @endpoint("/main_menu", ["GET", "POST"])
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
        try:
            decision_process = self.caseDB.get_decision_process(session["case_id"])
            if decision_process:
                context["process_menu"] = get_service(self.get_setting("protocol") + "://" + decision_process, 
                                                      "process_menu", case_id = session["case_id"])
        except:
            pass
        return render_template("main_menu.html", **context)


    @endpoint("/decision_process_request", ["GET", "POST"])
    def decision_process_request(self):
        """
        Endpoint which relays a request to the decision process associated with the currently active case.
        It always passes the current decision case id as a parameter in the request.
        """
        case_id = session["case_id"]
        decision_process = self.caseDB.get_decision_process(case_id)
        if decision_process:
            params = request.values.to_dict()
            del params["endpoint"]
            params["case_db"] = self.root_service_url
            params["case_id"] = case_id
            params["directories"] = json.dumps(self.service_directories)
            params["knowledge_repository"] = self.get_setting("knowledge_repository")
            response = requests.request(request.method, self.get_setting("protocol") + "://" + decision_process + "/" + request.values["endpoint"], 
                                        params = params)
            return self.main_menu_transition(main_dialogue = response.text)
        else:
            return "No decision process selected"
        
    
    @endpoint("/context_model_request", ["GET", "POST"])
    def context_model_request(self):
        """
        Endpoint which relays a request to the context model.
        It always passes the current decision case database url and case id as a parameter in the request.
        """
        context_service = self.get_setting("context_service")
        params = request.values.to_dict()
        del params["endpoint"]
        params["case_db"] = self.root_service_url
        params["case_id"] = session["case_id"]
        params["knowledge_repository"] = self.get_setting("knowledge_repository")
        response = requests.request(request.method, context_service + "/" + request.values["endpoint"], 
                                    params = params)
        return self.main_menu_transition(main_dialogue = response.text)
        
    
    @endpoint("/create_case_dialogue", ["GET"])
    def create_case_dialogue_transition(self):
        return render_template("create_case_dialogue.html")

    
    @endpoint("/open_case_dialogue", ["GET"])
    def open_case_dialogue_transition(self):
        # Create links to the user's cases
        links = ["<A HREF=\"/open_case?case_id=%s\">%s</A>" % pair for pair in self.caseDB.user_cases(session["user_id"])]

        dialogue = render_template("open_case_dialogue.html", user_cases = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/change_decision_process_dialogue", ["GET"])
    def change_decision_process_dialogue_transition(self):
        directories = self.get_setting("service_directories")
        services = []
        current_decision_process = self.caseDB.get_decision_process(session["case_id"])
        for d in directories:
            services += json.loads(get_service(self.get_setting("protocol") + "://" + d, "get_services", type = "decision_process"))
        options = ["<OPTION value=\"%s\" %s> %s </A>" % (s[2], "selected" if s[2] == current_decision_process else "", s[1]) for s in services]
        
        dialogue = render_template("change_decision_process_dialogue.html", decision_processes = options)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/add_stakeholder_dialogue", ["GET"])
    def add_stakeholder_dialogue_transition(self):
        # Create links to the decision processes
        # Get all users who exist both in the authentication list and in the case DB
        user_ids = [u for u in self.caseDB.user_ids() if self.authentication.user_exists(u)]
        users = [(u, self.authentication.get_user_name(u)) for u in user_ids]
        links = ["<A HREF=\"/add_stakeholder?user_id=%s\"> %s </A>" % pair for pair in users]
        
        dialogue = render_template("add_stakeholder_dialogue.html", stakeholders = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    @endpoint("/create_alternative_dialogue", ["GET"])
    def create_alternative_dialogue_transition(self):
        return render_template("create_alternative_dialogue.html")

    
    @endpoint("/edit_case_description_dialogue", ["GET"])    
    def edit_case_description_dialogue_transition(self):
        (title, description) = self.caseDB.get_case_description(session["case_id"])
        return render_template("edit_case_description_dialogue.html", title = title, description = description)

    
    @endpoint("/login_user", ["POST"])
    def login_user(self, user_id, password):
        """
        Endpoint representing the transition from the initial dialogue to the main menu.
        """
        if user_id == "" or password == "":
            # If user_id or password is missing, show the dialogue again with an error message
            return render_template("initial_dialogue.html", error = "FieldMissing")
        elif not self.authentication.user_exists(user_id):
            # If user_id does not exist, show the dialogue again with an error message
            return render_template("initial_dialogue.html", error = "NoSuchUser")
        elif not self.authentication.check_user_password(user_id, password):
            # If the wrong password was entered, show the dialogue again with an error message
            return render_template("initial_dialogue.html", error = "WrongPassword")
        else:
            # Login successful, save some data in the session object, and go to main menu
            session["user_id"] = user_id
            # Add the user to the case db if it is not already there
            self.caseDB.create_user(user_id)
            return self.main_menu_transition()


    @endpoint("/create_user", ["POST"])
    def create_user(self, user_id, password1, password2, name, email):
        """
        Endpoint representing the transition from the create user dialogue to the main menu.
        If the user exists, it returns to the create user dialogue and displays a message about this.
        As a transition action, it creates the new user in the database.
        """
        # TODO: Show the correct values pre-filled when the dialogue is reopened. 
        if self.authentication.user_exists(user_id):
            # If the user already exists, go back to the create user dialogue, with a message
            return render_template("create_user_dialogue.html", error = "UserExists")
        elif password1 != password2:
            return render_template("create_user_dialogue.html", error = "PasswordsNotEqual")
        else:
            # Otherwise, create the user in the database, and return to the initial dialogue.
            try:
                self.authentication.create_user(user_id, password1, email, name)
            except Exception as e:
                self.ms.logger.error("Failed to create user")
                self.ms.logger.error("Exception: " + str(e))
            return render_template("initial_dialogue.html")


    @endpoint("/confirm_account", ["POST"])
    def confirm_account(self, user_id, token):
        """
        Endpoint used by a user to confirm access to the email provided when setting up the account.
        It takes two parameters, namely user id and a token. 
        """
        if self.authentication.confirm_account(user_id, token):
            return "Account of " + user_id + " has been confirmed! You may now log in."
        else:
            return "Error: The token provided for validating account of " + user_id + " was not valid."
    
        
    @endpoint("/create_case", ["POST"])
    def create_case(self, title, description):
        """
        Endpoint representing the transition from the create case dialogue to the main menu.
        As a transition action, it creates the new case in the database, and connects the current user to it.
        """
        session["case_id"] = self.caseDB.create_case(title, description, session["user_id"])
        return self.main_menu_transition()


    @endpoint("/open_case", ["GET"])
    def open_case(self, case_id):
        # TODO: Instead of showing case id on screen, it should be the case name + id
        session["case_id"] = case_id
        return self.main_menu_transition()
        

    @endpoint("/logout", ["GET"])
    def logout(self):
        """
        Endpoint representing the transition to the logged out state, which is the same as the initial state.
        The user and case being worked on is deleted from the session.
        """
        session.pop("user_id", None)
        session.pop("case_id", None)
        return render_template("initial_dialogue.html")


    @endpoint("/change_password", ["GET"])
    def change_password(self):
        return self.main_menu_transition(main_dialogue = "Not yet implemented!")


    @endpoint("/change_case_description", ["POST"])
    def change_case_description(self, title, description):
        self.caseDB.change_case_description(session["case_id"], title, description)
        return self.main_menu_transition(main_dialogue = "Case description changed!")


    @endpoint("/change_decision_process", ["POST"])
    def change_decision_process(self, url):
        self.caseDB.change_decision_process(session["case_id"], url)
        menu = requests.get(self.get_setting("protocol") + "://" + url + "/process_menu", params = {"case_id": session["case_id"]}).text
        return self.main_menu_transition(main_dialogue = "Decision process changed!", process_menu = menu)


    @endpoint("/add_stakeholder", ["GET"])
    def add_stakeholder(self, user_id):
        """
        Adds a Stakeholder relationship between the current case and the user given as argument, with the role contributor.
        """
        self.caseDB.add_stakeholder(user_id, session["case_id"])
        return self.main_menu_transition(main_dialogue = "Stakeholder added!")


    @endpoint("/create_alternative", ["POST"])
    def create_alternative(self, title, description):
        """
        Adds a new decision alternative and adds a relation from the case to the alternative.
        """
        self.caseDB.create_alternative(title, description, session["case_id"])
        return self.main_menu_transition(main_dialogue = "New alternative created!")


    @endpoint("/export_case_to_knowledge_repository", ["GET"])
    def export_case_to_knowledge_repository(self):
        """
        Exports the current case to the knowledge repository.
        """
        description = self.caseDB.export_case_data(session["case_id"])
        requests.post(self.get_setting("knowledge_repository") + "/add_case", data = {"description": description})
        return self.main_menu_transition(main_dialogue = "The following case data was exported:\n\n" + description)
        

    @endpoint("/get_service_directories", ["GET"])
    def get_service_directories(self):
        """
        Returns the list of service directories registered with this service as a json file.
        """
        return Response(json.dumps(self.service_directories))

    
    @endpoint("/change_case_property", ["POST"])
    def change_case_property(self, case_id, name, value):
        """
        Changes a property of the indicated case id in the database.
        """
        self.caseDB.change_case_property(case_id, name, value)
        return Response("Ok")


    @endpoint("/get_decision_alternatives", ["GET"])
    def get_decision_alternatives(self, case_id):
        """
        Returns the list of decision alternatives associated with a case id, as a json file.
        """
        alternatives = self.caseDB.get_decision_alternatives(case_id)
        return Response(json.dumps(alternatives))
    

    @endpoint("/get_case_property", ["GET"])
    def get_case_property(self, case_id, name):
        """
        Gets the value of a certain property of the indicated case id in the database.
        """
        value = self.caseDB.get_case_property(case_id, name)
        return Response(value)

    
    @endpoint("/change_alternative_property", ["POST"])
    def change_alternative_property(self, alternative, name, value):
        """
        Changes a property of the indicated alternative in the database.
        """
        self.caseDB.change_alternative_property(alternative, name, value)
        return Response("Ok")


    @endpoint("/get_alternative_property", ["GET"])
    def get_alternative_property(self, alternative, name):
        """
        Gets the value of a certain property of the indicated alternative in the database.
        """
        value = self.caseDB.get_alternative_property(alternative, name)
        return Response(value)


    @endpoint("/github_update", ["GET", "POST"])
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
        
    
class DirectoryService(Microservice):
    
    """
    DirectoryMicroservices are used for providing catalogues of other services. They can be used by
    RootServices to look up services of different kinds.
    The list of services is stored in a local file on json format.
    
    The following methods are provided:
    /addService?type=X&name=Y&url=Z
    /removeService?url=Y
    /getServices[?type=X]
    
    TODO: Possibly, this could also run some tests of the service, to see that it fulfils the protocol.
    See also paper on SECO quality assurance, and select techniques from there.
    """
    
    def __init__(self, settings_file_name, handling_class = None, working_directory = None):
        """
        Initializes the microservice, and then reads the data file of registered services from a json file,
        or creates a json file if none exists.
        """
        super().__init__(settings_file_name, handling_class, working_directory)
        
        self.file_name = self.get_setting("directory_file_name")
        try:
            # Read file of services into a dictionary
            with open(os.path.join(self.working_directory, self.file_name), "r") as file:
                data = file.read()
                self.services = json.loads(data)
        except:
            # File of services does not exist, so create it an empty dictionary and save it to the file
            self.services = dict()
            data = json.dumps(self.services)
            with open(os.path.join(self.working_directory, self.file_name), "w") as file:
                file.write(data)
                
    
    @endpoint("/get_services", ["GET"])
    def get_services(self):
        """
        Returns a list of available services of the given type, in json format.
        To allow the user to manually edit the file, it is first read from file into self.services.
        Then this list is filtered.
        """
        with open(os.path.join(self.working_directory, self.file_name), "r") as file:
            data = file.read()
            self.services = json.loads(data)

        service_type = request.values["type"]
        if service_type:
            return json.dumps([s for s in self.services if s[0] == service_type])
        else:
            return json.dumps([s for s in self.services])


    @endpoint("/add_service", ["GET"])
    def add_service(self, service_type, name, url):
        """
        Adds a new service, with type, name, and URL, and saves the services file.
        If the given URL already exists, it should be removed.
        """
        self.services = [post for post in self.services if post[2] != url] + [(service_type, name, url)]
        with open(os.path.join(self.working_directory, self.file_name), "w") as file:
            json.dump(self.services, file, indent = 4)
        return ""


    @endpoint("/remove_service", ["GET"])
    def remove_service(self, url):
        """
        Removes a service based on its URL.
        """
        self.services = [post for post in self.services if post[2] != url]
        with open(os.path.join(self.working_directory, self.file_name), "w") as file:
            json.dump(self.services, file)
        return ""


class DecisionProcessService(Microservice):
    
    """
    Class for decision process microservices. It can provide a process menu to the Root Service, 
    and when the user selects different process steps, further endpoints of the decision process can be invoked. 
    """
    pass
    
#    def create_endpoints(self):
        # Initialize the default API
#        super(DecisionProcessService, self).create_endpoints()

        # Add endpoint for process menu.
#        self.ms.add_url_rule("/process_menu", view_func = self.endpoint_wrapper(self.process_menu))


class EstimationMethodService(Microservice):
    
    """
    Generic class for wrapping estimation methods into a web service. Normally, a contributer of an estimation method would not need to change this class,
    but only provide the handling EstimationMethod class.
    """
    
    def create_endpoints(self):
        # Initialize the default API
        super(EstimationMethodService, self).create_endpoints()

        # Add endpoint for estimation service specific methods
        self.ms.add_url_rule("/info", view_func = self.handling_class.as_view("info"))
        self.ms.add_url_rule("/dialogue", view_func = self.handling_class.as_view("dialogue"))
        self.ms.add_url_rule("/evaluate", view_func = self.handling_class.as_view("evaluate"))
        

class Method(View):

    """
    Base class for all methods, implementing the dispatch mechanism for service endpoints.
    All concrete subclasses should implement the following method:
    /info - implemented by the info method
    """

    def dispatch_request(self):
        """
        Dispatches each endpoint request to a separate function in the handling class.
        """
        # Call the method of the object that corresponds to the endpoint name
        result = getattr(self, request.endpoint)(self.get_params())

        # Create a response, and add some standard header information
        response = Response(result)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        return response


class EstimationMethod(Method):
    
    """
    This is the base class for EstimationMethods.
    Concrete instances should implement the following methods:
    /dialogue?param1=val1&...&paramN=valN - implemented by the dialogue method
    /evaluate?param1=val1&...&paramN=valN - implemented by the evaluate method
    """
    
    def get_params(self):
        """
        Returns a dictionary with value provided in the HTTP request for each of the
        parameters defined in the parameterNames() method defines in a subclass.
        """
        params = {}
        for n in self.parameter_names():
            params[n] = request.args.get(n, "")
        return params
    
    
    def dialogue(self, params):
        """
        Returns a HTML snippet with one text box for each parameter, which can be inserted into a web page.
        """
        
        entries = ""
        for n in self.get_params():
            entries = entries + n + ": <INPUT TYPE=\"text\" name=\"" + n + "\"><BR>"
        return entries
