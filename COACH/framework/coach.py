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
from inspect import getmro
import json
import logging
import os
import threading

# Web server framework
from flask import Flask, Response, request
from flask.views import View

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
    """
    return requests.post(url + "/"  + endpoint, data = kwargs).text


class Microservice:
    
    """
    Microservice is the base class of all microservices. It contains the functionality for setting up a service that can act as a stand-alone web server.
    It expects subclasses to implement the createEndpoints() function, which defines the service API.
    """
    
    def __init__(self, settings_file_name, handling_class = None, working_directory = None):
        """
        Initialize the microservice.
        """
        
        self.proxies = []
        
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
    
    
    @endpoint("/get_api", ["GET", "POST"])
    def get_api(self):
        """
        Returns the API of the Microservice as json data.
        """
        result = {}
        for (_, m) in inspect.getmembers(self):
            if hasattr(m, "url_path") and m.url_path != "/":
                record = {}
                record["methods"] = m.http_methods
                record["description"] = m.__doc__
                record["params"] = [p.name for (_, p) in inspect.signature(m).parameters.items()]
                result[m.url_path[1:]] = record
        return json.dumps(result)
    
    
    def create_proxy(self, url, method_preference = ["POST", "GET"], cache = True):
        """
        Returns a Proxy object representing the given url, and with method preferences as provided.
        If cache is True, the proxy is also stored in a list within the Microservice. This makes it
        possible to later query the Microservice for its proxies, to get a view of the architecture.
        """
        proxy = Proxy(url, method_preference)
        if cache:
            self.proxies += [proxy]
        return proxy


class Proxy():
    
    """
    Creates a proxy for a microservice specified by a URL. This makes it possible to make service calls as if they were made to a local
    instance of the object. It is recommended that Proxy objects are created through the create_proxy method in Microservice.
    """
    
    def __init__(self, url, method_preference):
        """
        Creates the proxy object. The url argument is the service which it acts as a proxy for. The method preferences is used in case
        a service endpoint accepts several methods, in which case the first applicable in the list is used.
        """
        self.url = url
        self.method_preference = method_preference
        
        # The api of the service is fetched when the first endpoint call is made, to allow for asynchronous initiations of services.
        self.api = None
        
        # TODO: Call the get_api service of the url here, and instantiate methods to represent each endpoint in its API.
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
                
                # Make the call
                result = requests.request(http_method, self.url + "/" + name, data = kwargs)
                
                # Decode json and return        
                return result.json()
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
