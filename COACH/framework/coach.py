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
import sys
import threading

# Web server framework
from flask import Flask, Response, request
import requests

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
        syspath0 = os.path.abspath(sys.path[0]) 
        return syspath0[0:syspath0.rfind("COACH")+len("COACH")]
    
    
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
        
        def highlight_text(s):
            """
            Prefix text with ###.
            """
            return "### " + s 
        
        def wrapping():
            """
            The endpoint wrapping fetches the request values supplied for each of the method's parameter names
            and adds them as arguments to the method. Trace output to the console can be obtained by setting
            the class variable trace to True.
            """
            args = [request.values[p.name] for (_, p) in inspect.signature(m).parameters.items()]
            if self.trace: 
                print(highlight_text(self.trace_indent * "    " + m.__name__ + "(" + ", ".join(args) + ")"))
                self.trace_indent += 1
            result = m(*args)
            if self.trace: 
                self.trace_indent -= 1
                print(highlight_text(self.trace_indent * "    " + "result from " + m.__name__ + ": " + (str(result).split("\n", 1)[0])))
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
            if hasattr(m, "url_path") and isinstance(m.url_path, str):
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
    
    
    @endpoint("/get_api", ["GET", "POST"])
    def get_api(self):
        """
        Returns the API of the Microservice as json data.
        """
        result = {}
        for (_, m) in inspect.getmembers(self):
            # To test if an attribute is part of the api, it must have the attribute url_path bound to a string.
            # All proxy objects will return that it has url_path bound to a function, which is why it also has to be checked for being a string.
            if hasattr(m, "url_path") and isinstance(m.url_path, str) and m.url_path != "/":
                record = {}
                record["methods"] = m.http_methods
                record["description"] = m.__doc__
                record["params"] = [p.name for (_, p) in inspect.signature(m).parameters.items()]
                result[m.url_path[1:]] = record
        return json.dumps(result)
    
    
    def create_proxy(self, url, method_preference = ["POST", "GET"], json_result = True, cache = True):
        """
        Returns a Proxy object representing the given url, and with method preferences as provided.
        If cache is True, the proxy is also stored in a dictionary within the Microservice. This makes it
        possible to later query the Microservice for its proxies, to get a view of the architecture.
        An attempt to create an already existing proxy will just return the existing one.
        """
        if cache:
            if url not in self.proxies:
                self.proxies[url] = Proxy(url, method_preference, json_result = json_result)
            return self.proxies[url]
        else:
            return Proxy(url, method_preference, json_result = json_result)


class Proxy():
    
    """
    Creates a proxy for a microservice specified by a URL. This makes it possible to make service calls as if they were made to a local
    instance of the object. It is recommended that Proxy objects are created through the create_proxy method in Microservice.
    """
    
    def __init__(self, url, method_preference, json_result):
        """
        Creates the proxy object. The url argument is the service which it acts as a proxy for. The method preferences is used in case
        a service endpoint accepts several methods, in which case the first applicable in the list is used.
        """
        self.url = url
        self.method_preference = method_preference
        self.json_result = json_result
        
        # The api of the service is fetched when the first endpoint call is made, to allow for asynchronous initiations of services.
        self.api = None
        

    def __getattr__(self, name):
        """
        __getattr__ is overridden to intercept any method call, and translate it to a corresponding service http request.
        Note that __getattr__ is only called by Python when an attribute was not found the usual way, so looking up
        explicitly defined attributes is not intercepted.
        """
        def service_call(*args, **kwargs):
            # On first service request, get the api of the service.
            if not self.api:
                self.api = requests.get(self.url + "/get_api").json()

            # Check if the endpoint exists, otherwise raise error
            if name in self.api:
                # Determine what http method to use, taking the first of the preferred method that the service supports.
                http_method = next(m for m in self.method_preference if m in self.api[name]["methods"])
                
                # Make the endpoint request
                result = requests.request(http_method, self.url + "/" + name, data = kwargs)
                
                # If there was an error in the response, raise an exception
                result.raise_for_status()
                
                # Return result, decoded as json if desired, and otherwise as text      
                if self.json_result:
                    return result.json()
                else:
                    return result.text
            else:
                raise AttributeError("Proxy has determined that service " + self.url + " does not provide endpoint for " + name)

        return service_call
    
    
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
    
    def __init__(self, settings_file_name, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)


    def parameter_names(self):
        """
        Returns the parameter names for this estimation method. Subclasses should redefine this method.
        """
        return []
    

    @endpoint("/dialogue", ["GET", "POST"])
    def dialogue(self):
        """
        Returns a HTML snippet with one text box for each parameter, which can be inserted into a web page.
        """
        
        entries = ""
        for n in self.parameter_names():
            entries = entries + n + ": <INPUT TYPE=\"text\" name=\"" + n + "\"><BR>"
        return Response(entries)