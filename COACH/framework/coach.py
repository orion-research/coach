"""  
Created on 16 mars 2016

@author: Jakob Axelsson

The module coach contains the framework for developing components for COACH in Python.
"""

# Standard libraries
import inspect
import json
import logging
import os
from string import Template
import sys
import threading
import traceback

# Web server framework
from flask import Flask, Response, request
import requests

# Database connection
from neo4j.v1 import GraphDatabase, basic_auth

# Auxiliary functions        
def endpoint(url_path = None, http_methods = ["POST", "GET"], content = "text/plain"):
    """
    endpoint is intended to be used as a decorator for the methods of a service class that should be used
    as endpoints. The function takes two arguments, a url path and a list of methods to be used with it.
    These arguments are added as attributes to the decorated method. This attributes are inspected by
    the create_endpoints method, and used to set up the method as an appropriate flask endpoint.

    If the url_path argument is not provided, the path is set to "/" + the function mane.
    If the http_methods are not provided, the default is ["POST", "GET"].
    If the content argument is not provided, it is set to "text/plain".
    """

    def decorator(f):
        if url_path:
            f.endpoint_url_path = url_path
        else:
            f.endpoint_url_path = "/" + f.__name__
        f.endpoint_http_methods = http_methods
        f.endpoint_content = content
        return f
    
    return decorator


# Endpoint content conversion defines a pair of functions that relates to a particular content type.
# The first function converts an object of the given type to a string, and the second does the inverse.
endpoint_content_conversion = {
    "text/plain" : (lambda x: x, lambda x: x),
    "text/html" : (lambda x: x, lambda x: x),
    "application/json" : (json.dumps, json.loads)
    }


class Microservice:
    
    """
    Microservice is the base class of all microservices. It contains the functionality for setting up a service that can act as a stand-alone web server.
    """
    
    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initialize the microservice.
        """
        
        # Create cache for proxies
        self.proxies = {}
        
        # Set the working directory to where the concrete class of which the microservice is an instance resides
        if working_directory:
            self.working_directory = working_directory
        else:
            self.working_directory = self.microservice_directory()
        os.chdir(self.working_directory)
        
        # Read settings from settings_file_name
#        self.load_settings(settings_file_name)
        self.load_settings()

        self.name = self.get_setting("name")
        self.host = self.get_setting("host")
        self.port = self.get_setting("port")

        # Create the microservice
        self.ms = Flask(self.name)
        self.ms.root_path = self.working_directory
        
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
            

    def coach_top_directory(self):
        """
        Returns the absolute file path to the top directory of the COACH installation.
        """
        
        # It is difficult to find a reliable way to determine the top directory that works on all kinds of system.
        # However, COACH top directory must be on the sys path of any module which is below it.
        s = "COACH"
        for p in sys.path:
            absp = os.path.abspath(p)
            if s in absp:
                return absp[0:absp.rfind(s) + len(s)]
#        syspath0 = os.path.abspath(sys.path[0])
#        return syspath0[0:syspath0.rfind("COACH")+len("COACH")]
    
    
    def microservice_directory(self):
        """
        Returns the absolute file path to the location of the source file of the class from which this microservice was instantiated.
        """
        # The module name determines the path from the top directory to where the module is located.
        return os.path.join(self.coach_top_directory(), *self.__module__.split(".")[1:-1])
    

    def load_settings(self, settings_file_name = None):
        """
        Loads settings from a file. If a settings file name is provided the settings are loaded from that file.
        If the file name was not provided, the function looks for a file called "settings.json", first in the same directory as 
        the class is defined, then in the subdirectory "settings", and finally in the COACH top directory.
        """
        fileData = ""
        if settings_file_name:
            with open(os.path.join(self.working_directory, os.path.normpath(settings_file_name)), "r") as file:
                fileData = file.read()
        else:
            try:
                with open(os.path.join(self.microservice_directory(), "settings.json"), "r") as file:
                    fileData = file.read()
            except OSError:
                try:
                    with open(os.path.join(self.microservice_directory(), "settings", "settings.json"), "r") as file:
                        fileData = file.read()
                except OSError:
                    with open(os.path.join(self.coach_top_directory(), "settings.json"), "r") as file:
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
        parents = [cls.__name__ for cls in inspect.getmro(self.__class__)]
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
            # All endpoint methods are given the attribute endpoint_url_path by the @endpoint decorator, which contains the url path,
            # and the attribute endpoint_http_methods, which contains a list of the http methods that it can be used with.
            if hasattr(m, "endpoint_url_path"):
                self.ms.add_url_rule(m.endpoint_url_path, view_func = self.endpoint_wrapper(m, m.endpoint_content), endpoint = m.__name__,
                                     methods = m.endpoint_http_methods)
                print("   - " + m.__name__ + " created")


    # Class variables trace and trace_indent are used to control console trace output from endpoint calls. 
    trace = True
    trace_indent = 0

    def endpoint_wrapper(self, m, content):
        
        def highlight_text(s):
            """
            Prefix text with ###.
            """
            return "### " + s 
        
        def wrapping():
            """
            The endpoint wrapping fetches the request values supplied for each of the method's parameter names
            and adds them as arguments to the method. Trace output to the console can be obtained by setting
            the class variable trace to True. The result from the method call is returned as a Response object.
            """
            request_args = request.get_json(force=True, silent=True)
            if not request_args:
                request_args = request.values

            args = []
            for (param_name, param) in inspect.signature(m).parameters.items():
                try:
                    args.append(request_args[param_name])
                except KeyError:
                    if param.default == inspect.Parameter.empty:
                        raise RuntimeError("Try to call the method {0} without the parameter {1}".format(m.__name__, param_name))
                    args.append(param.default)
                    
            if self.trace: 
                print(highlight_text(self.trace_indent * "    " + m.__name__ + "(" + str(args) + ")"))
                self.trace_indent += 1
            try:
                result = m(*args)
                if self.trace: 
                    self.trace_indent -= 1
                    print(highlight_text(self.trace_indent * "    " + "result from " + m.__name__ + ": " + (str(result).split("\n", 1)[0])))
                response = Response(endpoint_content_conversion[content][0](result), status = 200, content_type = content)
            except Exception:
                message = "An error occurred while processing the endpoint " + m.__name__ + ":\n"
                message += "Service: " + self.__class__.__name__ + " running at " + self.host + ":" + str(self.port) + "\n"
                message += "Arguments: " + str(args) + "\n"
                message += traceback.format_exc() + "\n\n"
                response = Response(message, status = 500, content_type = "text/plain")

            return response
        
        return wrapping
    
    
    @endpoint("/test_ui", ["GET", "POST"], "text/html")
    def test_ui(self):
        """
        Returns an automatically generated html page which allows testing of individual endpoints manually through 
        a web browser.
        """
        result = "<HTML>\n<H1>Endpoints of the microservice " + type(self).__name__ + "</H1>\n"
        result += "<P>NOTE: references to services should include the protocol and a trailing / (e.g. http://127.0.0.1:5002/)</P>"
        for (_, m) in inspect.getmembers(self):
            if hasattr(m, "endpoint_url_path") and isinstance(m.endpoint_url_path, str):
                result += "<FORM action=\"" + m.endpoint_url_path + "\""
                result += " method=\"" + m.endpoint_http_methods[0] + "\">\n"
                result += "<FIELDSET>\n"
                result += "<LEGEND><H2>" + m.endpoint_url_path + "</H2></LEGEND>\n"
                result += "<H3>HTTP method(s):</H3>" + ", ".join(m.endpoint_http_methods) + "<BR>\n"
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
    
    
    @endpoint("/get_api", ["GET", "POST"], "application/json")
    def get_api(self):
        """
        Returns the API of the Microservice as json data.
        """
        result = {}
        for (_, m) in inspect.getmembers(self):
            # To test if an attribute is part of the api, it must have the attribute endpoint_url_path bound to a string.
            # All proxy objects will return that it has endpoint_url_path bound to a function, which is why it also has to be checked for being a string.
            if hasattr(m, "endpoint_url_path") and isinstance(m.endpoint_url_path, str) and m.endpoint_url_path != "/":
                record = {}
                record["methods"] = m.endpoint_http_methods
                record["description"] = m.__doc__
                record["params"] = [p.name for (_, p) in inspect.signature(m).parameters.items()]
                result[m.endpoint_url_path[1:]] = record
        return result
    
    
    def create_proxy(self, url, method_preference = ["POST", "GET"], cache = True, **kwargs):
        """
        Returns a Proxy object representing the given url, and with method preferences as provided.
        If cache is True, the proxy is also stored in a dictionary within the Microservice. This makes it
        possible to later query the Microservice for its proxies, to get a view of the architecture.
        An attempt to create an already existing proxy will just return the existing one.
        
        If any kwargs are provided, they are stored and submitted automatically with each proxy call.
        """
        if cache:
            if url not in self.proxies:
                self.proxies[url] = Proxy(url, method_preference, **kwargs)
            return self.proxies[url]
        else:
            return Proxy(url, method_preference, **kwargs)


class MicroserviceException(Exception): pass


class Proxy():
    
    """
    Creates a proxy for a microservice specified by a URL. This makes it possible to make service calls as if they were made to a local
    instance of the object. It is recommended that Proxy objects are created through the create_proxy method in Microservice.
    """
    
    def __init__(self, url, method_preference, **kwargs):
        """
        Creates the proxy object. The url argument is the service which it acts as a proxy for. The method preferences is used in case
        a service endpoint accepts several methods, in which case the first applicable in the list is used.
        """
        self.url = url
        self.method_preference = method_preference

        # The api of the service is fetched when the first endpoint call is made, to allow for asynchronous initiations of services.
        self.api = None

        # A session is stored and reused to improve performance and also allow setting of e.g. cookies for testing purposes.
        self.session = None

        # Service http call results are stored, to allow inspection during testing.
        self.result = None
        

    def __getattr__(self, name):
        """
        __getattr__ is overridden to intercept any method call, and translate it to a corresponding service http request.
        Note that __getattr__ is only called by Python when an attribute was not found the usual way, so looking up
        explicitly defined attributes is not intercepted.
        """
        def service_call(*args, **kwargs):
            # Check if the right parameters are used
            if args:
                raise TypeError("Proxies can only be called with keyword parameters, position arguments are not yet supported")

            # On first service request, get the api of the service and create a session.
            if not self.api:
                self.api = requests.get(self.url + "/get_api").json()
                self.session = requests.Session()

            # Check if the endpoint exists, otherwise raise error
            if name in self.api:
                # Determine what http method to use, taking the first of the preferred method that the service supports.
                http_method = next(m for m in self.method_preference if m in self.api[name]["methods"])

                # Check that the parameter names used are in the api
                for p in kwargs:
                    if p not in self.api[name]["params"]:
                        raise TypeError("Parameter " + p + " is not defined for proxy method " + name + ". " +
                                        "Allowed parameters are " + ", ".join(self.api[name]["params"]) + ".")

                # The arguments are send in json to handle complex structure (nested dictionary, list...). 
                # However, this will fail if an argument is not serializable in json.
                kwargs_json = json.dumps(kwargs)
                # Make the endpoint request
                # TODO: change "data = kwargs_json" to "json = kwargs" ?
                self.result = self.session.request(http_method, self.url + "/" + name, data = kwargs_json)

                # If there was an error in the response, raise an exception
                if self.result.status_code != 200:
                    message = "An error occurred while processing the endpoint " + name + ":\n"
                    message += "Service: " + self.url + "\n"
                    message += "Arguments: " + str(kwargs) + "\n\n"
                    raise MicroserviceException(message + self.result.text)
                
                # Convert result to a Python object, depending on the content type
                if "Content-Type" in self.result.headers:
                    return endpoint_content_conversion[self.result.headers["Content-Type"]][1](self.result.text)
                else:
                    return self.result.text
            else:
                raise AttributeError("Proxy has determined that service " + self.url + " does not provide endpoint for " + name)

        return service_call
    
    
class GraphDatabaseService(Microservice):
    
    """
    Class for implementing a graph database storage service based on Neo4j. It contains functionality for initializing the
    database connection, making queries, and importing and exporting data based on semantic web triples.
    """
    
    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initiates the database at the provided url using the provided credentials.
        label indicates a label attached to all nodes used by this database, to distinguish them from nodes created by 
        other databases in the same DBMS.
        """
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        self.root_service_url = self.get_setting("protocol") + "://" + self.get_setting("host") + ":" + str(self.get_setting("port"))

        self.label = self.get_setting("label")
        
        # Store authentication service connection
        self.authentication_service_proxy = self.create_proxy(self.get_setting("authentication_service"))

        # Initiate neo4j
        try:
            self._db = GraphDatabase.driver("bolt://localhost", 
                                            auth=basic_auth(secret_data["neo4j_user_name"], 
                                                            secret_data["neo4j_password"]))
            self.ms.logger.info("Case database successfully connected")
            print("Case database successfully connected")
        except:
            self.ms.logger.error("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")
            print("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")
    
    
    def open_session(self):
        """
        Creates a database session and returns it.
        """    
        return self._db.session()
    
    
    def close_session(self, s):
        """
        Closes a database session.
        """
        s.close()
        

    def query(self, q, context = {}, session = None):
        """
        Function encapsulating the query interface to the database.
        q is the query string, and context is an optional dictionary containing parameters to be substituted into q.
        If a session is provided, the query is executed in that session. Otherwise, a session is created, used
        for the query, and then closed again.
        """
        try:
            # Add the label to the context, so that it can be used in queries
            context["label"] = self.label
            # Build query string by substituting template parameters with their context values
            q = Template(q).substitute(**context)
            if session:
                return session.run(q, context)
            else:
                # If no session was provided, create one for this query and close it when done
                s = self.open_session()
                result = s.run(q, context)
                self.close_session(s)
                return result
        except Exception as e:
            print("Error in database query: " + str(e))
    
   
    def get_graph_starting_in_node(self, start_node_id):
        """
        Return a 4-tuple where the first element is the set of node ids which can be reached by relations from the node with id = start_node.
        The second pair is a set of triples (n1, r, n2), where n1 and n2 are the ids of the nodes in a relation, and
        r is the id of the relation itself. 
        The third is mapping from ids to the properties of the node or relation with that id.
        The forth is a mapping from ids to the labels of nodes and types of relationships.
        The start_node_id parameter is an int, and the returned ids are also ints.
        """
        # Get nodes and edges by traversing relationships recursively starting in the node with case_id.
        visited_nodes = {start_node_id}
        edges = set()
        not_traversed = [start_node_id]
        while not_traversed:
            q = """MATCH (node1:$label) -[r]-> (node2:$label)
                   WHERE id(node1) = {node1_id}
                   RETURN id(node2) as node2_id, id(r) as r_id"""
            params = { "node1_id": not_traversed[0] }
            query_result = list(self.query(q, params))
            reached_nodes = { int(result["node2_id"]) for result in query_result }
            visited_nodes = visited_nodes | reached_nodes
            edges = edges | { (not_traversed[0], result["r_id"], result["node2_id"]) for result in query_result }
            not_traversed = not_traversed[1:] + list(reached_nodes - visited_nodes)

        # Get the properties and labels of all nodes
        properties = dict()
        labels = dict()
        for node_id in visited_nodes:
            q = """MATCH (node:$label)
                   WHERE id(node) = {node_id}
                   RETURN properties(node) as properties, labels(node) as label"""
            params = { "node_id": node_id }
            query_result = self.query(q, params).single()
            properties[node_id] = query_result["properties"]
            labels[node_id] = [label for label in query_result["label"] if label != self.label][0]
        
        # Get the properties and types of all relationships
        for (_, r_id, _) in edges:
            q = """MATCH (node1:$label) -[r]-> (node2:$label)
                   WHERE id(r) = {r_id}
                   RETURN properties(r) as properties, type(r) as label"""
            params = { "r_id": r_id }
            query_result = self.query(q, params).single()
            properties[r_id] = query_result["properties"]
            labels[r_id] = query_result["label"]
        
        return (visited_nodes, edges, properties, labels)
                
    
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
    Base clase for estimation method services. Subclasses should add the endpoints /info and /evaluate, and may redefine also the /dialogue endpoints.
    If the method has parameters, the subclasses should also redefine the method parameter_names.
    """
    
    def __init__(self, settings_file_name = None, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)


    def parameter_names(self):
        """
        Returns the parameter names for this estimation method. Subclasses should redefine this method.
        """
        return []
    

    @endpoint("/dialogue", ["GET", "POST"], "text/html")
    def dialogue(self, knowledge_repository):
        """
        Returns a HTML snippet with one text box for each parameter, which can be inserted into a web page.
        The URL for the knowledge repository is included as a parameter.
        """
        
        entries = ""
        for n in self.parameter_names():
            entries = entries + n + ": <INPUT TYPE=\"text\" name=\"" + n + "\"><BR>"
        return entries