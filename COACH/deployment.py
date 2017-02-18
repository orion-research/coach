"""
This module is a library for scripts that are used for deploying a set of COACH services on different system configurations.
The configurations include both local stand-alone local installation and server installation where a web server such as Apache is used.
The library contains functions to generate the necessary glue file for hosting services and ensure that everything is
properly linked.

Created on 18 nov. 2016

@author: Jakob Axelsson
"""

import datetime
import json
import os


class Service(object):
    """
    A Service object represents a COACH service.
    This is intended as an abstract class, where concrete services should always be subclasses.
    """

    def __init__(self, name, description, path):
        """
        Creates a Service object. Parameters are:
        - name: the name of the service used in file names etc.
        - description: a plain text description of the service, intended for human users.
        - path: the path where the source code of the service resides.
        """
        self.name = name
        self.description = description
        self.path = path
        
        
    def import_statement(self):
        """
        Returns an import statement for this service.
        This is used both for generating wsgi-files and launch files.
        """
        return "from COACH." + self.path + " import " + self.name + "\n"
        
        
    def directory_entry(self, configuration):
        """
        Generates a string indicating how the deployment of this service to a given configuration should be represented in a directory.
        If it should not be represented, None is returned. This is the default behavior, which is modified in some subclasses.
        """
        return None
        
        
    def wsgi(self, configuration):
        """
        Generates the content of a wsgi-file for this component, in order to make it callable from Apache.
        """

        template = """        
# wsgi file for the COACH {name} microservice, to make it useable from Apache.
# The script should be in the same directory as the Python file it imports.

import os
import sys

# Activate virtual environment
activate_this = '/var/www/developmentenv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

sys.path.append("/var/www/COACH/COACH/{file_path}")
sys.path.append("/var/www/COACH")

{import_statement}

if sys.version_info[0] < 3:
    raise Exception("Python 3 required! Current Python version is %s" % sys.version_info)


from COACH.framework import coach

application = {application}
"""
        
        return template.format(name = self.name, path = self.path, package_name = self.path.split(".")[-1], file_path = "/".join(self.path.split(".")), 
                             application = self.wsgi_application(configuration), import_statement = self.import_statement())

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        """
        template = """{package_name}.{name}(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    working_directory = "/var/www/COACH/COACH/{file_path}").ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)

    def virtual_host(self, port, configuration):
        """
        Returns a virtualhost entry into an apache conf file.
        """
        
        template = """
<virtualhost *:{port}>
    ServerName {base_url}
    WSGIDaemonProcess {daemon_name} user={user_name} group={group_name} threads=5 python-path=/var/www/COACH/COACH/{file_path}:/var/www/developmentenv/lib/python3.4/site-packages
    WSGIScriptAlias / /var/www/COACH/COACH/{file_path}/{name_lower}.wsgi

    SSLCertificateFile      /etc/letsencrypt/live/orion.sics.se/cert.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/orion.sics.se/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/orion.sics.se/chain.pem
    SSLEngine on

    <directory /var/www/COACH/COACH/{file_path}>
        WSGIProcessGroup {daemon_name}
        WSGIApplicationGroup %{{GLOBAL}}
        WSGIScriptReloading On
        Order deny,allow
        Allow from all
    </directory>
</virtualhost>     
"""
        return template.format(port = port, base_url = configuration.base_url, user_name = configuration.user_name, 
                               group_name = configuration.group_name, file_path = "/".join(self.path.split(".")),
                               name_lower = self.name.lower(), daemon_name = "coach-" + configuration.mode + "-" + self.name.lower())


    def minimal_functional_service(self):
        """
        Returns a string which is the Python code for a functional minimal service. The default behavior is to return None,
        which means that it is not possible to autogenerate a minimal functional service. Subclasses may override this.
        """
        return None
    
    
class InteractionService(Service):
    
    def __init__(self, name, description, path, database, directory_services, authentication, knowledge_repository_service, context_model_service):
        """
        Creates an InteractionService object. In addition to the Service, it has the following parameter:
        - database: the url to the database used for storing cases.
        - directory_services: a list of DirectoryServices used by the root service.
        - authentication: an AuthenticationService.
        - knowledge_repository_service: a KnowledgeRepositoryService used by the root service.
        - context_model_service: a ContextModelService used by the root service.
        """
        super().__init__(name, description, path)
        self.database = database
        self.directory_services = directory_services
        self.authentication = authentication
        self.knowledge_repository_service = knowledge_repository_service
        self.context_model_service = context_model_service


    def settings(self, configuration):
        """
        Returns the settings for a InteractionService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "database": configuration.service_url(self.database),
                "service_directories": [configuration.service_url(ds) for ds in self.directory_services],
                "logfile": "root.log",
                "authentication_service": configuration.service_url(self.authentication),
                "knowledge_repository": configuration.service_url(self.knowledge_repository_service),
                "context_service": configuration.service_url(self.context_model_service),
                "secret_data_file_name": "settings/root_secret_data.json"
                }


    def import_statement(self):
        """
        Returns an import statement for this service.
        This is used both for generating wsgi-files and launch files.
        """
        return "from COACH." + self.path + "." + self.name + " import " + self.name + "\n"


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        file_path = "/".join(self.path.split("."))
        result = """
    InteractionService().run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, file_path = file_path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The root service uses the application name coach.InteractionService, and has an extra argument point to the secret data.
        """
        template = """InteractionService().ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class AuthenticationService(Service):
    
    def __init__(self, name, description, path, authentication, email):
        """
        Creates an AuthenticationService object. In addition to the Service, it has the following parameter:
        - authentication: a file path to where the user authentication data is stored.
        - email: a dictionary of three fields, namely "server" (a string with the url to the email server); 
            "port" (an int); and "sender" (a string with an email address).
        """
        super().__init__(name, description, path)
        self.authentication = authentication
        self.email = email


    def settings(self, configuration):
        """
        Returns the settings for a AuthenticationService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "logfile": "root.log",
                "authentication_database": self.authentication,
                "email": self.email,
                "secret_data_file_name": "settings/root_secret_data.json"
                }


    def import_statement(self):
        """
        Returns an import statement for this service.
        This is used both for generating wsgi-files and launch files.
        """
        return "from COACH." + self.path + "." + self.name + " import " + self.name + "\n"


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        file_path = "/".join(self.path.split("."))
        result = """
    AuthenticationService().run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, file_path = file_path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The root service uses the application name coach.InteractionService, and has an extra argument point to the secret data.
        """
        template = """AuthenticationService().ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class CaseDatabase(Service):

    def __init__(self, name, description, path, label, authentication):
        """
        Creates a CaseDatabase object. 
        """
        super().__init__(name, description, path)
        self.label = label
        self.authentication = authentication
        

    def settings(self, configuration):
        """
        Returns the settings for a database object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "label": self.label,
                "authentication_service": configuration.service_url(self.authentication),
                "secret_data_file_name": "settings/root_secret_data.json"
                }


    def import_statement(self):
        """
        Returns an import statement for this service.
        This is used both for generating wsgi-files and launch files.
        """
        return "from COACH." + self.path + ".casedb import " + self.name + "\n"


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        file_path = "/".join(self.path.split("."))
        result = """
    CaseDatabase().run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, file_path = file_path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The case database service uses the application name coach.CaseDatabase, and has an extra argument point to the secret data and one for the node label.
        """
        template = """CaseDatabase().ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class DirectoryService(Service):
    
    def __init__(self, name, description, path, services):
        """
        Creates a DirectoryService object. In addition to the Service, it has the following parameter:
        - services: a list of services to be included in this directory.
        """
        super().__init__(name, description, path)
        self.services = services
        

    def settings(self, configuration):
        """
        Returns the settings for a DirectoryService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "directory_file_name": "settings/" + configuration.mode + "_directory.json"
                }

    
    def import_statement(self):
        """
        Returns an import statement for this service.
        This is used both for generating wsgi-files and launch files.
        """
        return "from COACH." + self.path + ".DirectoryService import " + self.name + "\n"


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        file_path = "/".join(self.path.split("."))
        result = """    
    DirectoryService(os.path.join(topdir, os.path.normpath("{settings_file_name}"))).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, file_path = file_path)


    def directory_entries(self, configuration):
        """
        Returns a list of directory entries. Services whose directory_entry method returns None are not included in the result.
        """
        entries = [s.directory_entry(configuration) for s in self.services]
        return [e for e in entries if e != None]

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The directory service uses the application coach.DirectoryService.
        """
        template = """DirectoryService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                        working_directory = os.path.abspath("/var/www/COACH/COACH/{file_path}")).ms"""
        return template.format(file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class ContextModelService(Service):

    def settings(self, configuration):
        """
        Returns the settings for a ContextModelService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "logfile": "ContextModel.log",
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        result = """    
    ContextModelService.ContextModelService(os.path.join(topdir, os.path.normpath("{settings_file_name}"))).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        """
        template = """ContextModelService.ContextModelService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    working_directory = "/var/www/COACH/COACH/{file_path}").ms"""
        return template.format(file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class KnowledgeRepositoryService(Service):
    
    def __init__(self, name, description, path, database):
        """
        Creates a KnowledgeRepositoryService object. In addition to the Service, it has the following parameter:
        - database: a url to the database where knowledge is stored.
        """
        super().__init__(name, description, path)
        self.database = database


    def settings(self, configuration):
        """
        Returns the settings for a KnowledgeRepositoryService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "database": self.database,
                "secret_data_file_name": "../framework/settings/root_secret_data.json"
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        result = """    
    wdir = os.path.join(topdir, "framework")
    os.chdir(wdir)
    KnowledgeRepositoryService.KnowledgeRepositoryService().run()
"""
        return result.format(settings_file_name = configuration.settings_file_name)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The knowledge repository service has an extra argument pointing to the secret data.
        """
        template = """{package_name}.{name}().ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)


class DecisionProcessService(Service):

    def directory_entry(self, configuration):
        """
        Returns a list representing a directory entry that indicates how this service is deployed on the given configuration.
        """
        return ["decision_process", self.description, configuration.service_url(self)] 


    def settings(self, configuration):
        """
        Returns the settings for a DecisionProcessService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "logfile": self.name + ".log",
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """
        
        file_path = "/".join(self.path.split("."))
        result = """    
    {name}.{name}(os.path.join(topdir, os.path.normpath("{settings_file_name}"))).run()
"""
        return result.format(name = self.name, file_path = file_path, settings_file_name = configuration.settings_file_name)


    def minimal_functional_service(self):
        """
        Returns a string which is the Python code for a functional minimal component of this kind.
        """
        template = """
# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class {name}(coach.DecisionProcessService):

    @endpoint("/process_menu", ["GET"])
    def process_menu(self):
        return "Automatically generated process menu for {name}"
        
if __name__ == '__main__':
        {name}(sys.argv[1]).run()
"""
        return template.format(name = self.name)


class EstimationMethodService(Service):

    def directory_entry(self, configuration):
        """
        Returns a list representing a directory entry that indicates how this service is deployed on the given configuration.
        """
        return ["estimation_method", self.description, configuration.service_url(self)] 

        
    def settings(self, configuration):
        """
        Returns the settings for a EstimationMethodService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """
        
        file_path = "/".join(self.path.split("."))
        result = """    
    {name}.{name}(os.path.join(topdir, os.path.normpath("{settings_file_name}"))).run()
"""
        return result.format(name = self.name, file_path = file_path, settings_file_name = configuration.settings_file_name)

    
    def minimal_functional_service(self):
        """
        Returns a string which is the Python code for a functional minimal component of this kind.
        """
        template = """
# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from flask import Response

# Coach framework
from COACH.framework.coach import endpoint, EstimationMethodService

class {name}(EstimationMethodService):
    
    def parameter_names(self):
        # If the estimation method has no parameters, this method can be removed.
        return []
    
    
    @endpoint("/info", ["GET", "PUT"])
    def info(self):
        return Response("This is a template for estimation methods. It currently takes no parameters, and always returns 0.")
    
    
    @endpoint("/evaluate", ["GET", "PUT"])
    def evaluate(self, params):
        return Response(str(0))


if __name__ == '__main__':
    {name}(sys.argv[1]).run()
"""
        return template.format(name = self.name)

    
class KnowledgeInferenceService(Service):

    def __init__(self, name, description, path, database, knowledge_repository):
        """
        Creates a KnowledgeRepositoryService object. In addition to the Service, it has the following parameter:
        - database: a url to the database where knowledge is stored.
        """
        super().__init__(name, description, path)
        self.database = database
        self.knowledge_repository = knowledge_repository


    def settings(self, configuration):
        """
        Returns the settings for a KnowledgeInferenceService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "database": configuration.service_url(self.database),
                "knowledge_repository": configuration.service_url(self.knowledge_repository)
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """
        
        file_path = "/".join(self.path.split("."))
        result = """    
    {name}.{name}(os.path.join(topdir, os.path.normpath("{settings_file_name}"))).run()
"""
        return result.format(name = self.name, file_path = file_path, settings_file_name = configuration.settings_file_name)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        """
        template = """KnowledgeInferenceService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                working_directory = os.path.abspath("/var/www/COACH/COACH/{file_path}")).ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)

    
class Configuration(object):
    """
    A Configuration object represents a machine on which COACH services can be deployed. 
    This is intended as an abstract class, where concrete configurations should always be subclasses.
    """

    def __init__(self, mode, base_url, services_with_ports, protocol, settings_file_name):
        """
        Creates a Configuration object. Parameters are:
        - mode: one of "local", "development", or "production"
        - base_url: a string consisting of the base url which is the base for all services deployed to it.
        - services_with_ports: a directory mapping service objects to port numbers.
        - protocol: the protocol used by the server, which is either "http" or "https".
        - settings_file_name: the path to the settings file for this configuration.
        """
        self.mode = mode
        self.base_url = base_url
        self.services_with_ports = services_with_ports
        self.protocol = protocol
        self.settings_file_name = settings_file_name
    
    
    def service_port(self, service):
        """
        Returns the port used for a certain service.
        """
        return self.services_with_ports[service]
    
    
    def service_url(self, service):
        """
        Returns the url of a certain service on this configuration.
        """
        return self.protocol + "://" + self.base_url + ":" + str(self.service_port(service))


    def generate_file(self, script_name, file_name, content):
        """
        Generates a file with the given file name and content. If the content string contains the formatting "{comment}", a comment is inserted
        stating that the file was generated by this script and the time and date. The parameter script_name contains the name of the script.
        """

        os_file_name = os.path.join(os.path.dirname(os.path.realpath(script_name)), os.path.normpath(file_name))
        print(" - Generating file " + os_file_name)
        with open(os_file_name, "w") as f:
            f.write(content)


    def generated_file_stamp(self, script_name):
        """
        Returns a stamp containing the script name and the date and time, suitable for inserting as a comment into generated files.
        """
        return "This file was automatically generated by the " + script_name + " script on " + str(datetime) + ".\n"
        
    
    def generate(self, script_name):
        """
        Generates the necessary files for this configuration.
        TODO: Output data to the correct files.
        """
        
        # Generate directory entries for all directory services allocated on this configuration.
        for s in self.services_with_ports.keys():
            if isinstance(s, DirectoryService):
                file_name = "/".join(s.path.split("."))+ "/settings/" + self.mode + "_directory.json"
                self.generate_file(script_name, file_name, json.dumps(s.directory_entries(self), indent = 4))
        
        # Generate the settings file
        # Create the result dictionary, initially containing the common settings for all objects.
        result = {"object": {
                             "description": "Common settings for all classes",
                             "mode": self.mode,
                             "host": self.base_url,
                             "protocol": self.protocol
                             }}
        for s in self.services_with_ports.keys():
            result[s.name] = s.settings(self)
        self.generate_file(script_name, self.settings_file_name, json.dumps(result, indent = 4))
        
        # Generate templates for services that do not yet have source code.        
        # - Templates for services that are not yet defined, i.e. where the "service_name.py" file does not exist. Includes the directory and __init__.py file.
        for s in self.services_with_ports.keys():
            # Check if a default minimal implementation is available
            code = s.minimal_functional_service()
            if code:
                # Check if the corresponding Python module already exists, and if not, generate it together with the necessary package structure.
                directory = os.path.realpath("COACH/" + "/".join(s.path.split(".")))
                file_name = os.path.join(directory, s.name + ".py")
                if os.path.isfile(file_name):
                    print(" - " + file_name + " already exists")
                else:
                    os.makedirs(directory, exist_ok = True)
                    self.generate_file(script_name, file_name, code)
                    open(directory + "/__init__.py", "a").close()


class LocalConfiguration(Configuration):
    """
    A LocalConfiguration object represents an environment where COACH is ran stand-alone. 
    """
    
    def generate(self, script_name):
        """
        Generates the necessary files for this configuration.
        """
        super().generate(script_name)
        
        # Generate the launch_local.py file for launching all services on a local machine.
        launch_local = "# " + self.generated_file_stamp(script_name)
        launch_local += """
import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir))

from COACH.framework import coach
"""
        
        for s in self.services_with_ports.keys():
            launch_local += s.import_statement()

        launch_local += """
if __name__ == '__main__':
    # Start root service and directory service from the framework module
    topdir = os.path.dirname(os.path.abspath(__file__))
    wdir = os.path.join(topdir, "framework")
    os.chdir(wdir)
    
    # Start all the services
"""

        for s in self.services_with_ports.keys():
            launch_local += s.launch_statement(self)
        self.generate_file(script_name, "launch_local.py", launch_local)
        

class ApacheConfiguration(Configuration):
    """
    An ApacheConfigurationObject represents an environment where Apache is used for deploying COACH.
    """

    def __init__(self, mode, base_url, services_with_ports, protocol, settings_file_name, 
                 user_name, group_name):
        """
        Creates an ApacheConfiguration object. It extends the Configuration constructor with the following parameters:
        - user_name: the user name under which the Apache server is running.
        - group_name: the group name under which the Apache server is running.
        """
        super().__init__(mode, base_url, services_with_ports, protocol, settings_file_name)
        self.user_name = user_name
        self.group_name = group_name


    def generate(self, script_name):
        """
        Generates the necessary files for this configuration.
        """
        super().generate(script_name)

        # Apache .conf file for each configuration.
        content = "# " + self.generated_file_stamp(script_name)
        for (s, p) in self.services_with_ports.items():
            if not isinstance(s, InteractionService):
                content += "Listen " + str(p) + "\n"
                
        for (s, p) in self.services_with_ports.items():
            content += s.virtual_host(p, self)
        self.generate_file(script_name, "coach-" + self.mode + ".conf", content)
        
        # Apache .wsgi files for each component.
        for s in self.services_with_ports.keys():
            content = "# " + self.generated_file_stamp(script_name) + s.wsgi(self)
            self.generate_file(script_name, "/".join(s.path.split(".")) + "/" + s.name.lower() + ".wsgi", content)


