"""
This module is a library for scripts that are used for deploying a set of COACH services on different system configurations.
The configurations include both local stand-alone local installation and server installation where a web server such as Apache is used.
The library contains functions to generate the necessary glue file for hosting services and ensure that everything is
properly linked.

TODO:
- Put them in the correct files instead of on the terminal. 

- Templates for services that are not yet defined, i.e. where the "<service_name>.py" file does not exist. 
Includes the directory and __init__.py file. Method in each subclass of Service (primarily this is for decision models and estimation methods).


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
        return "from " + self.path + " import " + self.name + "\n"
        
        
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

sys.path.append("/var/www/COACH/{file_path}")
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
                                                    working_directory = "/var/www/COACH/{file_path}").ms"""
        return template.format(name = self.name, package_name = self.path.split(".")[-1], 
                               file_path = "/".join(self.path.split(".")), settings_file_name = configuration.settings_file_name)

    def virtual_host(self, port, configuration):
        """
        Returns a virtualhost entry into an apache conf file.
        """
        
        template = """
<virtualhost *:{port}>
    ServerName {base_url}
    WSGIDaemonProcess {daemon_name} user={user_name} group={group_name} threads=5 python-path=/var/www/COACH/{file_path}:/var/www/developmentenv/lib/python3.4/site-packages
    WSGIScriptAlias / /var/www/COACH/{file_path}/{name_lower}.wsgi

    SSLCertificateFile      /etc/letsencrypt/live/orion.sics.se/cert.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/orion.sics.se/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/orion.sics.se/chain.pem
    SSLEngine on

    <directory /var/www/COACH/{file_path}>
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
    
class RootService(Service):
    
    def __init__(self, name, description, path, database, directory_services, authentication, knowledge_repository_service, context_model_service, email):
        """
        Creates a RootService object. In addition to the Service, it has the following parameter:
        - database: the url to the database used for storing cases.
        - directory_services: a list of DirectoryServices used by the root service.
        - authentication: a file path to where the user authentication data is stored.
        - knowledge_repository_service: a KnowledgeRepositoryService used by the root service.
        - context_model_service: a ContextModelService used by the root service.
        - email: a dictionary of three fields, namely "server" (a string with the url to the email server); 
            "port" (an int); and "sender" (a string with an email address).
        """
        super().__init__(name, description, path)
        self.database = database
        self.directory_services = directory_services
        self.authentication = authentication
        self.knowledge_repository_service = knowledge_repository_service
        self.context_model_service = context_model_service
        self.email = email


    def settings(self, configuration):
        """
        Returns the settings for a RootService object in the given configuration.
        """
        return {"description": "Settings for " + self.name,
                "name": self.description,
                "port": configuration.service_port(self),
                "database": self.database,
                "service_directories": [configuration.service_url(ds) for ds in self.directory_services],
                "logfile": "root.log",
                "authentication_database": self.authentication,
                "knowledge_repository": configuration.service_url(self.knowledge_repository_service, protocol = True),
                "context_service": configuration.service_url(self.context_model_service, protocol = True),
                "email": self.email
                }


    def import_statement(self):
        """
        Returns an empty string, since Root services do not need an import statement.
        """
        return ""


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        path = "/".join(self.path.split(".")[1:])
        result = """
    wdir = os.path.join(topdir, os.path.normpath("{path}"))
    os.chdir(wdir)
    coach.RootService(os.path.join(topdir, os.path.normpath("{settings_file_name}")), 
                      os.path.normpath("settings/root_secret_data.json"),
                      working_directory = wdir).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, path = path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The root service uses the application name coach.RootService, and has an extra argument point to the secret data.
        """
        template = """coach.RootService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    os.path.normpath("/var/www/COACH/COACH/framework/settings/root_secret_data.json"),
                                                    working_directory = os.path.abspath("/var/www/COACH/{file_path}")).ms"""
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
        Returns an empty string, since directory services do not need an import statement.
        """
        return ""


    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        path = "/".join(self.path.split(".")[1:])
        result = """    
    wdir = os.path.join(topdir, os.path.normpath("{path}"))
    os.chdir(wdir)
    coach.DirectoryService(os.path.join(topdir, os.path.normpath("{settings_file_name}")), 
                           working_directory = os.path.join(topdir, "framework")).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, path = path)


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
        template = """coach.DirectoryService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    working_directory = os.path.abspath("/var/www/COACH/{file_path}")).ms"""
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

        path = "/".join(self.path.split(".")[1:])
        result = """    
    wdir = os.path.join(topdir, os.path.normpath("context_model"))
    os.chdir(wdir)
    ContextModelService.ContextModelService(os.path.join(topdir, os.path.normpath("{settings_file_name}")), 
                                                              working_directory = wdir).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, path = path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        """
        template = """ContextModelService.ContextModelService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    working_directory = "/var/www/COACH/{file_path}").ms"""
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
                }

    
    def launch_statement(self, configuration):
        """
        Returns a Python statement that launches this service in a given configuration.
        """

        path = "/".join(self.path.split(".")[1:])
        result = """    
    wdir = os.path.join(topdir, "framework")
    os.chdir(wdir)
    KnowledgeRepositoryService.KnowledgeRepositoryService(os.path.join(topdir, os.path.normpath("{settings_file_name}")), 
                                                    os.path.normpath("settings/root_secret_data.json"),
                                                    working_directory = wdir).run()
"""
        return result.format(settings_file_name = configuration.settings_file_name, path = path)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        The knowledge repository service has an extra argument pointing to the secret data.
        """
        template = """{package_name}.{name}(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    os.path.normpath("/var/www/COACH/COACH/framework/settings/root_secret_data.json"),
                                                    working_directory = os.path.abspath("/var/www/COACH/{file_path}")).ms"""
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
        
        path = "/".join(self.path.split(".")[1:])
        result = """    
    wdir = os.path.join(topdir, os.path.normpath("{path}"))
    os.chdir(wdir)
    {name}.{name}(os.path.join(topdir, os.path.normpath("{settings_file_name}")), working_directory = wdir).run()
"""
        return result.format(name = self.name, path = path, settings_file_name = configuration.settings_file_name)
    

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
        
        path = "/".join(self.path.split(".")[1:])
        result = """    
    wdir = os.path.join(topdir, os.path.normpath("{path}"))
    os.chdir(wdir)
    coach.EstimationMethodService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                              handling_class = {name}.{name},
                              working_directory = wdir).run()
"""
        return result.format(name = self.name, path = path, settings_file_name = configuration.settings_file_name)

    
    def wsgi_application(self, configuration):
        """
        Returns the wsgi application call for this service.
        For an estimation method, the application is apways coach.EstimationMethodService, which takes an extra argument 
        indicating the handling class.
        """
        template = """coach.EstimationMethodService(os.path.normpath("/var/www/COACH/COACH/{settings_file_name}"),
                                                    handling_class = {package_name}.{name},
                                                    working_directory = "/var/www/COACH/{file_path}").ms"""
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
    
    
    def service_url(self, service, protocol = False):
        """
        Returns the url of a certain service on this configuration.
        """
        if protocol:
            return self.protocol + "://" + self.base_url + ":" + str(self.service_port(service))
        else:
            return self.base_url + ":" + str(self.service_port(service))


    def generate_file(self, script_name, file_name, content):
        """
        Generates a file with the given file name and content. If the content string contains the formatting "{comment}", a comment is inserted
        stating that the file was generated by this script and the time and date. The parameter script_name contains the name of the script.
        """

#        print(os.path.dirname(os.path.realpath(script_name)))
#        print(os.path.normpath(file_name))
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
                file_name = "/".join(s.path.split(".")[1:])+ "/settings/" + self.mode + "_directory.json"
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
        
        
        # - Templates for services that are not yet defined, i.e. where the "service_name.py" file does not exist. Includes the directory and __init__.py file.
    
        
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
    try:
        # This will work if running script from command line (Windows or Linux)
        # For some reason, it does not work if starting from within Eclipse
        topdir = os.path.abspath(os.curdir)
        
        # Start root service and directory service from the framework module
        wdir = os.path.join(topdir, "framework")
        os.chdir(wdir)
    except:
        # Workaround for starting in Eclipse
        topdir = os.path.join(os.path.abspath(os.curdir), "COACH")

        # Start root service and directory service from the framework module
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
                 user_name, group_name, certificate_path, python_path):
        """
        Creates an ApacheConfiguration object. It extends the Configuration constructor with the following parameters:
        - user_name: the user name under which the Apache server is running.
        - group_name: the group name under which the Apache server is running.
        - certificate_path: the file path to the security certificates used by Apache.
        - python_path: the file path to where Python is installed.
        """
        super().__init__(mode, base_url, services_with_ports, protocol, settings_file_name)
        self.user_name = user_name
        self.group_name = group_name
        self.certificate_path = certificate_path
        self.python_path = python_path


    def generate(self, script_name):
        """
        Generates the necessary files for this configuration.
        """
        super().generate(script_name)

        # Apache .conf file for each configuration.
        content = "# " + self.generated_file_stamp(script_name)
        for (s, p) in self.services_with_ports.items():
            if not isinstance(s, RootService):
                content += "Listen " + str(p) + "\n"
                
        for (s, p) in self.services_with_ports.items():
            content += s.virtual_host(p, self)
        self.generate_file(script_name, "coach-" + self.mode + ".conf", content)
        
        # Apache .wsgi files for each component.
        for s in self.services_with_ports.keys():
            content = "# " + self.generated_file_stamp(script_name) + s.wsgi(self)
            self.generate_file(script_name, "/".join(s.path.split(".")[1:]) + "/" + s.name.lower() + ".wsgi", content)


