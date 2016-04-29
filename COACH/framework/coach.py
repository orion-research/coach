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
import hashlib
import json
import logging
import os
import random
import smtplib
import ssl
import string
import threading

# Web server framework
from flask import Flask, Response, request, session
from flask.views import View
from flask.templating import render_template

import requests

# Database connection
from neo4jrestclient.client import GraphDatabase


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
        with open(os.path.join(self.working_directory, os.path.normpath(settings_file_name)), "r") as file:
            fileData = file.read()
        self.settings = json.loads(fileData)

        self.name = self.settings["name"]
        self.host = self.settings["host"]
        self.port = self.settings["port"]

        # Create the microservice
        self.ms = Flask(self.name)
        
        # If a log file name is provided, enable logging to that file
        if "logfile" in self.settings:
            handler = logging.FileHandler(self.settings["logfile"])
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.ms.logger.addHandler(handler)
            self.ms.logger.warning("Logging started")

        # Setup SSL encryption
        # See http://flask.pocoo.org/snippets/111/. Keys and certificates can be generated here: http://www.selfsignedcertificate.com/.
#        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
#        self.ssl_context.load_cert_chain(self.settings["ssl_certificate"], self.settings["ssl_encryption_key"])
    
        # Initialize the endpoints, as defined in concrete subclasses
        self.create_endpoints()
            

    def run(self):
        """
        Starts the MicroService.
        """
        
        # Depending on the server mode, start the app in different ways
        if self.settings["mode"] == "local":
            # Run using Flask built in server with debugging on

            # Start the microservice in a separate thread, since the call does not return otherwise.
            # Also, use threaded=True, to allow the microservice to handle multiple requests.
            # To be able to run the debug mode, it is necessary to turn off the automatic reloading.
            # TODO: The SSL encryption does not seem to work, so it is turned off right now.
    #        self.thread = threading.Thread(target = self.ms.run, kwargs = {"port": self.port, "ssl_context": self.ssl_context})
            self.thread = threading.Thread(target = self.ms.run, kwargs = {"host": self.host, "port": self.port, "use_reloader": False, "threaded": True, "debug": True})
            self.thread.start()
        elif self.settings["mode"] in ["development", "production"]:
            # Run using Flask built in server with debugging on
            # TODO: Later, maybe change this to running with Tornado or other framework
            self.thread = threading.Thread(target = self.ms.run, kwargs = {"host": self.host, "port": self.port, "use_reloader": False, "threaded": True, "debug": False})
            self.thread.start()
        else:
            self.ms.logger.error("Unknown server mode: " + self.settings["mode"])
            

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


class Authentication:
    """
    The Authentication class provides storage for the information about users (user id, name, password hash, etc.)
    This information is stored in a json file, containing a dictionary with user name as key and the other information as a value dictionary. 
    Also, it provides functionality for generating and handling tokens. Token related information is not stored persistently. 
    """

    def __init__(self, users_filename):
        """
        Initializes the user database from file, if the file exists, or otherwise creates an empty file.
        """
        self.users_filename = users_filename
        try:
            # Read users from the file name
            with open(self.users_filename, "r") as file:
                data = file.read()
                self.users = json.loads(data)
        except:
            # File of services does not exist, so create it an empty dictionary and save it to the file
            self.users = dict()
            data = json.dumps(self.users)
            with open(self.users_filename, "w") as file:
                file.write(data)


    def user_exists(self, userid):
        """
        Returns True if the user with the given id already exists, and False otherwise.
        """
        return userid in self.users
    

    def create_user(self, userid, password, email, name):
        """
        Adds a user with the given id to the database. The password is stored as a hashed value.
        If the userid already exists in the database, that information is overwritten.
        """ 
        self.users[userid] = {"password_hash": self.password_hash(password), "email": email, "name": name}
        with open(self.users_filename, "w") as file:
            json.dump(self.users, file)

        """
        TODO: Add this functionality
        
        # Send an email to the user.
        # TODO: Remove the gmail info, put it into the settings file.
        # TODO: Create a link to an endpoint where the user can validate the password.
        gmail_address = "noreply.orionresearch@gmail.com"
        gmail_password = "<password deleted>"
        token = self.get_random_token(20)

        message_text = "To validate your COACH user identity, please follow this link: blablabla.com/" + token

        message = "\From: %s\nTo: %s\nSubject: %s\n\n%s" % (gmail_address, email, "Your COACH account", message_text)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, email, message)
            server.close()
            self.ms.logger.info("Successfully sent mail to " + email)
        except Exception as e:
            self.ms.logger.error("Failed to send mail to " + email)
            self.ms.logger.error("Exception: " + str(e))
        """
        return None
    

    def password_hash(self, password):
        """
        Returns the salted hash value for the given password.
        See https://wiki.python.org/moin/Md5Passwords.
        """
        salt = "fe5x19"
        return hashlib.md5((salt + password).encode("UTF-8")).hexdigest()
        
    
    def check_user_password(self, userid, password):
        """
        Returns True if the hash of the given password matches the one stored in the database, and otherwise False.
        """
        if userid in self.users:
            return self.users[userid]["password_hash"] == self.password_hash(password)
        else:
            return False 
    
    
    def get_user_email(self, userid):
        """
        Returns the email of a user.
        """
        return self.users[userid]["email"]
    
    
    def get_user_name(self, userid):
        """
        Returns the name of a user.
        """
        return self.users[userid]["name"]


    def get_random_token(self, length):
        """
        Generates a random token, i.e. a string of alphanumeric characters, of the requested length.
        """
        return "".join([random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) 
                        for _ in range(0, length)])


class CaseDatabase:
    
    """
    The case database provides the interface to the database for storing case information. It wraps an API around a standard graph DBMS.
    
    TODO: 
    - Probably, it is wise to use Neo4j's query language as much as possible, to minimize dependency
    on the rest library.
    - These actions should also generate entries into a history, showing who, when, and what has been done. 
    """

    def __init__(self, url, username, password):
        self._db = GraphDatabase(url, username = username, password = password)


    def users(self, user_id = None):
        """
        Queries the case database and returns an iterable of the users with the given id, or all users is no user_id is provided.
        
        TODO: replace with the following query:
        q = MATCH (u: User) WHERE u.user_id = %s RETURN u % user_id 
        q = MATCH (u: User) RETURN u 
        """
        try:
            if user_id:
                return self._db.labels.get("User").get(user_id = user_id)
            else:
                return self._db.labels.get("User").all()
        except:
            # Label did not exist, so create it and return the empty list
            self._db.labels.create("User")
            return []
    
    
    def user_cases(self, user_id):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        q = """MATCH (case: Case) -[Stakeholder]-> (user {user_id: \"%s\"}) RETURN id(case), case.title""" % user_id
        return [(case_id, case_title) for (case_id, case_title) in self._db.query(q)]
        
    
    def create_user(self, user_id):
        """
        Creates a new user in the database, if it does not exist already.
        """
        if len(self.users(user_id)) == 0:
            new_user = self._db.nodes.create(user_id = user_id)
            new_user.labels.add("User")


    def create_case(self, title, description, initiator):
        """
        Creates a new case in the database, with a relation to the initiating user. It returns the database id of the new case.
        """
        new_case = self._db.nodes.create(title = title, description = description)
        new_case.labels.add("Case")
        
        # Mark the current user as a stakeholder and initiator of this decision case
        new_case.relationships.create("Stakeholder", initiator, role = "initiator")
        return new_case.id
        
    
    def add_stakeholder(self, user_id, case_id):    
        user_node = self._db.labels.get("User").get(user_id = user_id)[0]
        case_node = self._db.nodes[case_id]
        case_node.relationships.create("Stakeholder", user_node, role = "contributor")

    
    def create_alternative(self, title, description, case_id):
        """
        Creates a decision alternative and links it to the case.
        """
        case_node = self._db.nodes[case_id]
        new_alternative = self._db.nodes.create(title = title, description = description)
        new_alternative.labels.add("Alternative")
        case_node.relationships.create("Alternative", new_alternative)

    
    def get_decision_process(self, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = %s RETURN case.decision_process LIMIT 1""" % case_id
            # Why is the result a list of lists????
            # Probably, because each return can contain several elements and hence they are gathered in a list
            return self._db.query(q)[0][0]
        except:
            return None
    
    
    def change_decision_process(self, case_id, url):
        """
        Changes the decision process url associated with a case.
        """

        q = """MATCH (case: Case) WHERE id(case) = %s SET case.decision_process = \"%s\"""" % (case_id, url)
        self._db.query(q)

    
    def change_case_property(self, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        q = """MATCH (case: Case) WHERE id(case) = %s SET case.%s = \"%s\"""" % (case_id, name, value)
        self._db.query(q)
        
    
    def get_case_property(self, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = %s RETURN case.%s""" % (case_id, name)
            return self._db.query(q)[0][0]
        except:
            return None
        
    
    def get_decision_alternatives(self, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        TODO: The query needs to be fixed. It does not check that the case is correct.
        """
#        q = """MATCH (case: Case) -[:Alternative]-> (alt: Alternative) WHERE id(case) = %s RETURN alt.title, id(alt)""" % (case_id,)
        q = """MATCH (case: Case) -[:Alternative]-> (alt: Alternative) WHERE id(case) = {case_id} RETURN alt.title, id(alt)""".format(**locals())
        return list(self._db.query(q))
    
    
    def change_alternative_property(self, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        q = """MATCH (alt: Alternative) WHERE id(alt) = %s SET alt.%s = \"%s\"""" % (alternative, name, value)
        self._db.query(q)
        
    
    def get_alternative_property(self, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        try:
            q = """MATCH (alt: Alternative) WHERE id(alt) = %s RETURN alt.%s""" % (alternative, name)
            return self._db.query(q)[0][0]
        except:
            return None
        
    
class RootService(Microservice):
    
    """
    RootService implements the overall workflow manager and decision case manager. It is configured with links to 
    a number of directories, which are used for searching for other services. It contains the basic
    functionality for logging in, registering users, creating and closing decision cases, attaching
    users to a decision case, and selecting the decision process. Every installation of COACH has exactly one instance of this class.
    """
    
    def __init__(self, settings_file_name, secret_args, handling_class = None, working_directory = None):
        """
        Initialize the RootService object. The secret_args argument should be a list of three strings:
        1. The database user name.
        2. The database password.
        3. The session encryption key.
        These are kept outside the settings file to ensure that they do not spread when files are shared in a repository.
        """
        
        super().__init__(settings_file_name, handling_class = handling_class, working_directory = working_directory)

        # Setup encryption for settings cookies
        self.ms.secret_key = secret_args[2]

        # Initialize the user database
        self.authentication = Authentication(os.path.join(self.working_directory, self.settings["authentication_database"]))

        # Initialize the case database
        try:
            self.caseDB = CaseDatabase(self.settings["database"], 
                                       secret_args[0], 
                                       secret_args[1])
            self.ms.logger.info("Case database successfully connected")
        except:
            self.ms.logger.error("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")

        # Store point to service directories
        self.service_directories = self.settings["service_directories"]
                
    
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
        
        # Endpoints for transitions between the states without side effects
        self.ms.add_url_rule("/", view_func = self.initial_transition)
        self.ms.add_url_rule("/create_user_dialogue", view_func = self.create_user_dialogue_transition)
        self.ms.add_url_rule("/main_menu", view_func = self.main_menu_transition, methods = ["GET", "POST"])
        self.ms.add_url_rule("/create_case_dialogue", view_func = self.create_case_dialogue_transition)
        self.ms.add_url_rule("/open_case_dialogue", view_func = self.open_case_dialogue_transition)
        self.ms.add_url_rule("/change_decision_process_dialogue", view_func = self.change_decision_process_dialogue_transition)
        self.ms.add_url_rule("/add_stakeholder_dialogue", view_func = self.add_stakeholder_dialogue_transition)
        self.ms.add_url_rule("/create_alternative_dialogue", view_func = self.create_alternative_dialogue_transition)
        
        # Endpoints for transitions between states with side effects
        # TODO: Do all these have to be posts, to ensure that data is encrypted when HTTPS is implemented?
        self.ms.add_url_rule("/login_user", view_func = self.login_user, methods = ["POST"])
        self.ms.add_url_rule("/create_user", view_func = self.create_user, methods = ["POST"])
        self.ms.add_url_rule("/create_case", view_func = self.create_case, methods = ["POST"])
        self.ms.add_url_rule("/logout", view_func = self.logout)
        self.ms.add_url_rule("/change_password", view_func = self.change_password)
        self.ms.add_url_rule("/open_case", view_func = self.open_case)
        self.ms.add_url_rule("/edit_case_description", view_func = self.edit_case_description)
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
        directories = self.settings["service_directories"]
        services = []
        current_decision_process = self.caseDB.get_decision_process(session["case_id"])
        for d in directories:
            services += json.loads(requests.get(d + "/get_services?type=decision_process").text)
        options = ["<OPTION value=\"%s\" %s> %s </A>" % (s[2], "selected" if s[2] == current_decision_process else "", s[1]) for s in services]
        
        dialogue = self.go_to_state(self.change_decision_process_dialogue, decision_processes = options)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def add_stakeholder_dialogue_transition(self):
        # Create links to the decision processes
        users = [(u["user_id"], u["name"]) for u in self.caseDB.users()]
        links = ["<A HREF=\"/add_stakeholder?user_id=%s\"> %s </A>" % pair for pair in users]
        
        dialogue = self.go_to_state(self.add_stakeholder_dialogue, stakeholders = links)
        return self.main_menu_transition(main_dialogue = dialogue)

    
    def create_alternative_dialogue_transition(self):
        return self.go_to_state(self.create_alternative_dialogue)

    
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
        user = self.caseDB.users(session["user_id"])[0]
        
        session["case_id"] = self.caseDB.create_case(title, description, user)
        
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


    def edit_case_description(self):
        return self.main_menu_transition(main_dialogue = "Not yet implemented!")


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
        
        self.file_name = self.settings["directory_file_name"]
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
