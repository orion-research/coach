"""
Created on 16 mars 2016

@author: Jakob Axelsson

The module coach contains the framework for developing components for COACH in Python.


TODO:
Deviations from architecture description:
- Add a simple knowledge repository microservice, with only the ability to export a case to it

Security:
- How to handle authentication and database read/write access from other services?
- Is it possible to restrict access for a client to only query on a limited set of the database? If so, this could be a way of letting 
services use general querys. Otherwise, the root must provide an API for a limited set of requests.
- The general principle for the external services is that they get access to one node in the database.
To that node they may add attributes, and they may create subnodes linked from it.
All this should happen through an API in the root service. The database itself should not be visible on the Internet.
- Look into security. Authentication, e.g. http://blog.miguelgrinberg.com/post/restful-authentication-with-flask.
HTTPS, e.g. http://stackoverflow.com/questions/29458548/can-you-add-https-functionality-to-a-python-flask-web-server. https://github.com/kennethreitz/flask-sslify. 
- In the root settings, it should be possible set a regexp for what email addresses are allowed, to limit user creation.
- Make https work!
- It is necessary to have some kind of token to ensure that access is valid after logging it. Could it be saved in the session object?
http://stackoverflow.com/questions/32510290/how-do-you-implement-token-authentication-in-flask.
For each user, a token with expiration is generated, and the token is also stored in the session object.
Whenever an endpoint requiring authentication is called, it checks if the session token is still valid.
If so, it gets a new token, and the timer is reset. If the token is no longer valid, the user is logged out.
This can all be put into one method self.authenticate(), which is called at the beginning of each endpoint.
- An email should be sent (e.g. using a special gmail account) to ask users to verify when registering.

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
and possible be alerted through email when in production. See http://flask.pocoo.org/docs/0.10/errorhandling/.
"""

# Standard libraries
from inspect import getmro
import json
import logging
import os
import subprocess
        
import threading

# Coach modules
from COACH.framework.authentication import Authentication
from COACH.framework.casedb import CaseDatabase

# Web server framework
from flask import Flask, Response, request, session
from flask.views import View
from flask.templating import render_template

import requests



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
        Override this method in subclasses to add service endpoints.
        """
        pass


    def create_state(self, state_dialogue, endpoint = None):
        """
        Creates a state that can be used in state machine like control flows.
        state_dialogue is the name of the html template file to be rendered when the state is entered.
        Currently, the state is just the dialogue file name.
        If endpoint is provided, that endpoint is added to the list of endpoints.
        """
        
        if endpoint:
            self.ms.add_url_rule(endpoint, view_func = lambda : self.go_to_state(state_dialogue))
        return state_dialogue

    
    def go_to_state(self, s, **kwargs):
        """
        Enters the state s, and displays its dialogue.
        The optional kwargs are variables that can be evaluated when rendering the dialogue.
        """
        return render_template(s, **kwargs)


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

        # Initialize the user database
        self.authentication = Authentication(os.path.join(self.working_directory, self.get_setting("authentication_database")))

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
            return subprocess.check_output(["git", "describe", "--all", "--long"]).decode("ascii")
        except:
            return "No version information available"

    
    def create_endpoints(self):
        # States, represented by dialogues
        self.initial_state = self.create_state("initial_dialogue.html")
        self.create_user_dialogue = self.create_state("create_user_dialogue.html")
        self.main_menu_state = self.create_state("main_menu.html")
        self.create_case_dialogue = self.create_state("create_case_dialogue.html")
        self.open_case_dialogue = self.create_state("open_case_dialogue.html")
        self.change_decision_process_dialogue = self.create_state("change_decision_process_dialogue.html")
        self.add_stakeholder_dialogue = self.create_state("add_stakeholder_dialogue.html")
        self.create_alternative_dialogue = self.create_state("create_alternative_dialogue.html")
        self.edit_case_description_dialogue = self.create_state("edit_case_description_dialogue.html")
        
        # Endpoints for transitions between the states without side effects
        self.ms.add_url_rule("/", view_func = self.initial_transition)
        self.ms.add_url_rule("/create_user_dialogue", view_func = self.create_user_dialogue_transition)
        self.ms.add_url_rule("/main_menu", view_func = self.main_menu_transition, methods = ["GET", "POST"])
        self.ms.add_url_rule("/create_case_dialogue", view_func = self.create_case_dialogue_transition)
        self.ms.add_url_rule("/open_case_dialogue", view_func = self.open_case_dialogue_transition)
        self.ms.add_url_rule("/change_decision_process_dialogue", view_func = self.change_decision_process_dialogue_transition)
        self.ms.add_url_rule("/add_stakeholder_dialogue", view_func = self.add_stakeholder_dialogue_transition)
        self.ms.add_url_rule("/create_alternative_dialogue", view_func = self.create_alternative_dialogue_transition)
        self.ms.add_url_rule("/edit_case_description_dialogue", view_func = self.edit_case_description_dialogue_transition)
        
        # Endpoints for transitions between states with side effects
        # TODO: Do all these have to be posts, to ensure that data is encrypted when HTTPS is implemented?
        self.ms.add_url_rule("/login_user", view_func = self.login_user, methods = ["POST"])
        self.ms.add_url_rule("/create_user", view_func = self.create_user, methods = ["POST"])
        self.ms.add_url_rule("/create_case", view_func = self.create_case, methods = ["POST"])
        self.ms.add_url_rule("/logout", view_func = self.logout)
        self.ms.add_url_rule("/change_password", view_func = self.change_password)
        self.ms.add_url_rule("/open_case", view_func = self.open_case)
        self.ms.add_url_rule("/change_case_description", view_func = self.change_case_description, methods = ["POST"])
        self.ms.add_url_rule("/change_decision_process", view_func = self.change_decision_process, methods = ["POST"])
        self.ms.add_url_rule("/add_stakeholder", view_func = self.add_stakeholder)
        self.ms.add_url_rule("/create_alternative", view_func = self.create_alternative, methods = ["POST"])

        # Endpoints for database and directory services for usage by other components
        self.ms.add_url_rule("/get_service_directories", view_func = self.get_service_directories)
        self.ms.add_url_rule("/change_case_property", view_func = self.change_case_property, methods = ["POST"])
        self.ms.add_url_rule("/get_case_property", view_func = self.get_case_property)
        self.ms.add_url_rule("/get_decision_alternatives", view_func = self.get_decision_alternatives)
        self.ms.add_url_rule("/change_alternative_property", view_func = self.change_alternative_property, methods = ["POST"])
        self.ms.add_url_rule("/get_alternative_property", view_func = self.get_alternative_property)
        

    def initial_transition(self):
        # Store the software version in the session object
        session["version"] = self.get_version()

        return self.go_to_state(self.initial_state)


    def create_user_dialogue_transition(self):
        return self.go_to_state(self.create_user_dialogue)

    
    def main_menu_transition(self, **kwargs):
        """
        Transition to the main menu. If the argument main_dialogue is passed with the call, it is first fetched from the URLs provided.
        If the case in the database has a decision method selected, its process method is fetched and included in the context.
        """
        context = kwargs
        for arg in ["main_dialogue"]:
            url = request.values.get(arg)
            if url:
                # Fetch data from the provided url, passing the url of the root server as an argument to allow database access etc.
                context[arg] = requests.get(url, params = {"root": request.url_root}).text
        # If 
        if "message" in request.values:
            context["message"] = request.values["message"]
        try:
            decision_process = self.caseDB.get_decision_process(session["case_id"])
            if decision_process:
                context["process_menu"] = requests.get("http://" + decision_process + "/process_menu", params = {"case_id": session["case_id"]}).text
        except:
            pass
        return self.go_to_state(self.main_menu_state, **context)

    
    def create_case_dialogue_transition(self):
        return self.go_to_state(self.create_case_dialogue)

    
    def open_case_dialogue_transition(self):
        # Create links to the user's cases
        links = ["<A HREF=\"/open_case?case_id=%s\">%s</A>" % pair for pair in self.caseDB.user_cases(session["user_id"])]

        dialogue = self.go_to_state(self.open_case_dialogue, user_cases = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def change_decision_process_dialogue_transition(self):
        directories = self.get_setting("service_directories")
        services = []
        current_decision_process = self.caseDB.get_decision_process(session["case_id"])
        for d in directories:
            services += json.loads(requests.get(d + "/get_services?type=decision_process").text)
        options = ["<OPTION value=\"%s\" %s> %s </A>" % (s[2], "selected" if s[2] == current_decision_process else "", s[1]) for s in services]
        
        dialogue = self.go_to_state(self.change_decision_process_dialogue, decision_processes = options)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def add_stakeholder_dialogue_transition(self):
        # Create links to the decision processes
        # Get all users who exist both in the authentication list and in the case DB
        user_ids = [u for u in self.caseDB.user_ids() if self.authentication.user_exists(u)]
        users = [(u, self.authentication.get_user_name(u)) for u in user_ids]
        links = ["<A HREF=\"/add_stakeholder?user_id=%s\"> %s </A>" % pair for pair in users]
        
        dialogue = self.go_to_state(self.add_stakeholder_dialogue, stakeholders = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def create_alternative_dialogue_transition(self):
        return self.go_to_state(self.create_alternative_dialogue)

    
    def edit_case_description_dialogue_transition(self):
        (title, description) = self.caseDB.get_case_description(session["case_id"])
        return self.go_to_state(self.edit_case_description_dialogue, title = title, description = description)

    
    def login_user(self):
        """
        Endpoint representing the transition from the initial dialogue to the main menu.
        """
        user_id = request.form["user_id"]
        password = request.form["password"]
        
        if user_id == "" or password == "":
            # If user_id or password is missing, show the dialogue again with an error message
            return self.go_to_state(self.initial_state, error = "FieldMissing")
        elif not self.authentication.user_exists(user_id):
            # If user_id does not exist, show the dialogue again with an error message
            return self.go_to_state(self.initial_state, error = "NoSuchUser")
        elif not self.authentication.check_user_password(user_id, password):
            # If the wrong password was entered, show the dialogue again with an error message
            return self.go_to_state(self.initial_state, error = "WrongPassword")
        else:
            # Login successful, save some data in the session object, and go to main menu
            session["user_id"] = user_id
            # Add the user to the case db if it is not already there
            self.caseDB.create_user(user_id)
            return self.main_menu_transition()


    def create_user(self):
        """
        Endpoint representing the transition from the create user dialogue to the main menu.
        If the user exists, it returns to the create user dialogue and displays a message about this.
        As a transition action, it creates the new user in the database.
        """
        
        user_id = request.form["user_id"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]
        name = request.form["name"]
        email = request.form["email"]
        
        # TODO: Show the correct values pre-filled when the dialogue is reopened. 
        if self.authentication.user_exists(user_id):
            # If the user already exists, go back to the create user dialogue, with a message
            return self.go_to_state(self.create_user_dialogue, error = "UserExists")
        elif password1 != password2:
            return self.go_to_state(self.create_user_dialogue, error = "PasswordsNotEqual")
        else:
            # Otherwise, create the user in the database, and return to the initial dialogue.
            self.authentication.create_user(user_id, password1, email, name)
            return self.go_to_state(self.initial_state)


    def create_case(self):
        """
        Endpoint representing the transition from the create case dialogue to the main menu.
        As a transition action, it creates the new case in the database, and connects the current user to it.
        """
        
        title = request.form["title"]
        description = request.form["description"]
        
        session["case_id"] = self.caseDB.create_case(title, description, session["user_id"])
        
        return self.main_menu_transition()


    def open_case(self):
        # TODO: Instead of showing case id on screen, it should be the case name + id

        session["case_id"] = request.values["case_id"]

        return self.main_menu_transition()
        

    def logout(self):
        """
        Endpoint representing the transition to the logged out state, which is the same as the initial state.
        The user and case being worked on is deleted from the session.
        """
        session.pop("user_id", None)
        session.pop("case_id", None)
        return self.go_to_state(self.initial_state)


    def change_password(self):
        return self.main_menu_transition(main_dialogue = "Not yet implemented!")


    def change_case_description(self):
        title = request.form["title"]
        description = request.form["description"]
        self.caseDB.change_case_description(session["case_id"], title, description)

        return self.main_menu_transition(main_dialogue = "Case description changed!")


    def change_decision_process(self):
        url = request.form["url"]
        self.caseDB.change_decision_process(session["case_id"], url)
        menu = requests.get("http://" + url + "/process_menu").text

        return self.main_menu_transition(main_dialogue = "Decision process changed!", process_menu = menu)


    def add_stakeholder(self):
        """
        Adds a Stakeholder relationship between the current case and the user given as argument, with the role contributor.
        """
        user_id = request.args.get("user_id", None)
        self.caseDB.add_stakeholder(user_id, session["case_id"])
        return self.main_menu_transition(main_dialogue = "Stakeholder added!")


    def create_alternative(self):
        """
        Adds a new decision alternative and adds a relation from the case to the alternative.
        """
        title = request.form["title"]
        description = request.form["description"]
        self.caseDB.create_alternative(title, description, session["case_id"])
        return self.main_menu_transition(main_dialogue = "New alternative created!")


    def get_service_directories(self):
        """
        Returns the list of service directories registered with this service as a json file.
        """
        return Response(json.dumps(self.service_directories))

    
    def change_case_property(self):
        """
        Changes a property of the indicated case id in the database.
        """
        self.caseDB.change_case_property(request.values["case_id"], request.values["name"], request.values["value"])
        return Response("Ok")


    def get_decision_alternatives(self):
        """
        Returns the list of decision alternatives associated with a case id, as a json file.
        """
        alternatives = self.caseDB.get_decision_alternatives(request.values["case_id"])
        return Response(json.dumps(alternatives))
    
    
    def get_case_property(self):
        """
        Gets the value of a certain property of the indicated case id in the database.
        """
        value = self.caseDB.get_case_property(request.values["case_id"], request.values["name"])
        return Response(value)

    
    def change_alternative_property(self):
        """
        Changes a property of the indicated case id in the database.
        """
        self.caseDB.change_alternative_property(request.values["alternative"], request.values["name"], request.values["value"])
        return Response("Ok")


    def get_alternative_property(self):
        """
        Gets the value of a certain property of the indicated alternative in the database.
        """
        value = self.caseDB.get_alternative_property(request.values["alternative"], request.values["name"])
        return Response(value)

    
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
                
    
    def create_endpoints(self):
        # Initialize the API
        self.ms.add_url_rule("/get_services", view_func = self.get_services)
        self.ms.add_url_rule("/add_service", view_func = self.add_service)
        self.ms.add_url_rule("/remove_service", view_func = self.remove_service)


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


    def add_service(self):
        """
        Adds a new service, with type, name, and URL, and saves the services file.
        If the given URL already exists, it should be removed.
        """
        service_type = request.args.get("type", "")
        name = request.args.get("name", "")
        url = request.args.get("url", "")
        
        self.services = [post for post in self.services if post[2] != url] + [(service_type, name, url)]
        with open(os.path.join(self.working_directory, self.file_name), "w") as file:
            json.dump(self.services, file)
        return ""


    def remove_service(self):
        """
        Removes a service based on its URL.
        """
        url = request.args.get("url", "")
        
        self.services = [post for post in self.services if post[2] != url]
        with open(os.path.join(self.working_directory, self.file_name), "w") as file:
            json.dump(self.services, file)
        return ""


class DecisionProcessService(Microservice):
    
    """
    Class for decision process microservices. It can provide a process menu to the Root Service, 
    and when the user selects different process steps, further endpoints of the decision process can be invoked. 
    """
    
    def create_endpoints(self):
        # Initialize the API
        self.ms.add_url_rule("/process_menu", view_func = self.process_menu)


class EstimationMethodService(Microservice):
    
    """
    Generic class for wrapping estimation methods into a web service. Normally, a contributer of an estimation method would not need to change this class,
    but only provide the handling EstimationMethod class.
    """
    
    def create_endpoints(self):
        # Initialize the API
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
