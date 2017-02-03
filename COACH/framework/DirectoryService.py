'''
Created on 16 jan. 2017

@author: Jakob Axelsson
'''


# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Web service framework
from flask import request

# Standard libraries
import json


class DirectoryService(coach.Microservice):
    
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
    
    def __init__(self, settings_file_name, working_directory = None):
        """
        Initializes the microservice, and then reads the data file of registered services from a json file,
        or creates a json file if none exists.
        """
        super().__init__(settings_file_name, working_directory)
        
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