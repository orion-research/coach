'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Standard libraries
import json

# Semantic web framework
import rdflib
import sqlalchemy
from rdflib_sqlalchemy.store import SQLAlchemy


class CaseDatabase(coach.GraphDatabaseService):
    
    """
    The case database provides the interface to the database for storing case information. 
    It wraps an API around a standard graph DBMS.
    
    TODO: 
    - All actions should generate entries into a history, showing who, when, and what has been done.
    This is useful for being able to analyze decision processes. 
    """

    def __init__(self, settings_file_name = None, working_directory = None):
        """
        The case database is initialized by loading the ontology from file.
        """
        
        super().__init__(settings_file_name, working_directory = working_directory)

        filepath = os.path.join(self.microservice_directory(), "settings", "coach_case_db.db")
        ident = rdflib.URIRef("coach_case_db")
#            store = rdflib.plugin.get("SQLAlchemy", rdflib.store.Store)(identifier = ident)

        # TODO: This works on Windows, but probably not on Unix.
        # See http://docs.sqlalchemy.org/en/latest/dialects/sqlite.html#module-sqlalchemy.dialects.sqlite.pysqlite, under Connect strings
        self.db_uri = "sqlite:///" + filepath
        self.store = SQLAlchemy(identifier = ident, engine = sqlalchemy.create_engine(self.db_uri))
        self.graph = rdflib.ConjunctiveGraph(store = self.store, identifier = ident)

        # Open the database file, creating it if it does not already exist.
        if not os.path.isfile(filepath):
            print("Creating new triple store at " + self.db_uri)
            self.store.open(rdflib.Literal(self.db_uri), create = True)
        else:
            print("Connected existing triple store at " + self.db_uri)
            self.store.open(rdflib.Literal(self.db_uri), create = False)

        self.orion_ns = "http://www.orion-research.se/ontology#"  # The name space for the ontology used
        self.data_ns = self.get_setting("protocol") + "://" + self.host + ":" + str(self.port) + "/data#"  # The name space for this data source

        # Namespace objects cannot be stored as object attributes, since they collide with the microservice mechanisms
        orion_ns = rdflib.Namespace(self.orion_ns)
        data_ns = rdflib.Namespace(self.data_ns)

        ontology_context = orion_ns.ontology_context

        print("Contexts = " + str([c.identifier for c in self.graph.contexts()]))
        print("Ontology context = " + str(self.graph.get_context(ontology_context)))
        print("Number of statements in the database: " + str(len(self.graph)))
        print("Namespaces in database: " + str([ns for ns in self.graph.namespaces()]))

        # Remove the ontology data, and reload it to ensure that it is updated to latest version
        self.ontology = self.graph.get_context(ontology_context)
        if self.ontology:
            print("Removing context triples from ontology")
            self.ontology.remove((None, None, None))
            print("Number of statements in the database after removing ontology: " + str(len(self.graph)))
            print("Namespaces in database after removing ontology: " + str([ns for ns in self.graph.namespaces()]))
        else:
            print("Creating new ontology")
            self.ontology = rdflib.Graph(store = self.store, identifier = ontology_context)

        print("Loading new ontology data")
        ontology_path = os.path.join(self.working_directory, os.pardir, "Ontology.ttl")
        print("Namespaces in ontology: " + str([ns for ns in self.ontology.namespaces()]))
        # An error message is produced when parsing, but the data is still read.
        # It appears to relate to the binding of namespaces in the ontology.
        # It could possibly be the addition of a default namespace when one already exists.
        self.ontology.parse(source = ontology_path, format = "ttl")
        print("Number of statements in the database after (re)loading ontology: " + str(len(self.graph)))
        print("Namespaces in ontology after (re)loading: " + str([ns for ns in self.ontology.namespaces()]))

        self.ontology.bind("data", data_ns, override = True)
        self.ontology.bind("orion", orion_ns, override = True)

        print("Loaded " + self.orion_ns + " ontology with " + str(len(self.ontology)) + " statements")

        q = """SELECT ?c WHERE { ?c a orion:Case . }"""
        print("Sample query: Get all the cases in the database")
        qres = self.graph.query(q)
        for (a,) in qres:
            print(a)

    
    @endpoint("/restore_users", ["GET", "POST"], "text/plain")
    def restore_users(self):
        """
        Add all registered users to the database, if they are not already present. 
        This is used to restore users if the case database was cleared.
        """
        # Using rdflib, there is no need to add users to the database. They are implicitly added whenever
        # a triple containing the user URI is added. Querying for existing users is to the authentication service.
        return "Ok"

    
    def is_stakeholder(self, user_id, case_id):
        """
        Returns true if user_id is a stakeholder in case_id.
        """
        q = "ASK WHERE { ?case_id orion:role ?r . ?r orion:person ?user_id . }"
        result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                  initBindings = { "case_id": rdflib.URIRef(case_id),
                                                  "user_id": rdflib.URIRef(self.authentication_service_proxy.get_user_uri(user_id = user_id)) })
        return next(r for r in result)


    def is_stakeholder_in_alternative(self, user_id, case_id, alternative):
        """
        Returns true if alternative is linked to a case where the user_id is a stakeholder.
        """
        q = "ASK WHERE { ?case_id orion:role ?r . ?r orion:person ?user_id . ?case_id orion:alternative ?alternative . }"
        result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                  initBindings = { "case_id": rdflib.URIRef(case_id), "user_id": rdflib.URIRef(self.authentication_service_proxy.get_user_uri(user_id = user_id)),
                                                  "alternative": rdflib.URIRef(alternative) })
        return result


    @endpoint("/user_ids", ["POST"], "application/json")
    def user_ids(self, user_id, user_token):
        """
        Queries the case database and returns an iterable of all user ids (the name the user uses to log in).
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            # When using rdflib, the user is identified with an uri which consists of the authentication service url + user_id.
            return [user_name for (user_name, _, _, _) in self.authentication_service_proxy.get_users()]
        else:
            return "Invalid user token"
         
    
    @endpoint("/user_cases", ["GET"], "application/json")
    def user_cases(self, user_id, user_token):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = "SELECT ?case_id ?case_title WHERE { ?case_id orion:role ?r . ?r orion:person ?user_id . ?case_id orion:title ?case_title }"
            result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "user_id": self.authentication_service_proxy.get_user_uri(user_id = user_id) })
            return list(result)
        else:
            return "Invalid user token"
        
    
    @endpoint("/case_users", ["GET"], "application/json")
    def case_users(self, user_id, user_token, case_id):
        """
        Returns a list of ids of the users who are currently stakeholders in the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = "SELECT ?user_id WHERE { ?case_id orion:role ?r . ?r orion:person ?user_id . }"
            result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "case_id": case_id })
            return [u for (u,) in result]
        else:
            return "Invalid user token"
        
        
    @endpoint("/create_user", ["POST"], "application/json")
    def create_user(self, user_id, user_token):
        """
        Creates a new user in the database, if it is not already there. 
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            # When using rdflib, users are not stored in the case database, so no operations are needed.
            pass
        else:
            return "Invalid user token"
        

    @endpoint("/create_case", ["POST"], "application/json")
    def create_case(self, title, description, user_id, user_token):
        """
        Creates a new case in the database, with a relation to the initiating user (referenced by user_id). 
        It returns the database id of the new case.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            # Generate a new uri for the new case by finding the largest current uri and adding 1 to it
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = self.new_uri()
            role = self.new_uri()

            # Create a new graph for this case, with the uri as its context identifier
            case_graph = rdflib.Graph(store = self.store, identifier = rdflib.URIRef(case_id))

            # Add title and description
            case_graph.add((case_id, orion_ns.title, rdflib.Literal(title)))
            case_graph.add((case_id, orion_ns.description, rdflib.Literal(description)))
            case_graph.add((case_id, rdflib.RDF.type, orion_ns.Case))

            # Create the relationships to an initial role with initiator as the person
            case_graph.add((case_id, orion_ns.role, role))
            case_graph.add((role, rdflib.RDF.type, orion_ns.Role))
            case_graph.add((role, orion_ns.person, rdflib.URIRef(self.authentication_service_proxy.get_user_uri(user_id = user_id))))
            case_graph.commit()

            for t in case_graph:
                print(str(t))
            return str(case_id)
        else:
            return "Invalid user token"
        
    
    @endpoint("/change_case_description", ["POST"], "application/json")
    def change_case_description(self, user_id, user_token, case_id, title, description):
        """
        Changes the title and description fields of the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            case_graph.set((case_id, orion_ns.title, rdflib.Literal(title)))
            case_graph.set((case_id, orion_ns.description, rdflib.Literal(description)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"
           
    
    @endpoint("/get_case_description", ["GET"], "application/json")    
    def get_case_description(self, user_id, user_token, case_id):
        """
        Returns a tuple containing the case title and description for the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            title = case_graph.value(case_id, orion_ns.title, None, "")
            description = case_graph.value(case_id, orion_ns.description, None, "")
            return (title, description)
        else:
            return "Invalid user token"
        

    @endpoint("/add_stakeholder", ["POST"], "application/json")
    def add_stakeholder(self, user_id, user_token, case_id, stakeholder, role):
        """
        Adds a user as a stakeholder with the provided role to the case. 
        If the user is already a stakeholder, nothing is changed. 
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            role = self.new_uri()
            case_graph = self.graph.get_context(case_id)

            # Create the relationships to an initial role with initiator as the person
            case_graph.add((case_id, orion_ns.role, role))
            case_graph.add((role, rdflib.RDF.type, orion_ns.Role))
            case_graph.add((role, orion_ns.person, rdflib.URIRef(stakeholder)))
            case_graph.commit()

            return "Ok"
        else:
            return "Invalid user token"


    @endpoint("/add_alternative", ["POST"], "application/json")    
    def add_alternative(self, user_id, user_token, title, description, case_id):
        """
        Adds a decision alternative and links it to the case.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)

            alternative = self.new_uri()
            case_graph.add((case_id, orion_ns.alternative, alternative))
            case_graph.add((alternative, rdflib.RDF.type, orion_ns.Alternative))
            case_graph.add((alternative, orion_ns.title, rdflib.Literal(title)))
            case_graph.add((alternative, orion_ns.description, rdflib.Literal(description)))

            case_graph.commit()

            return str(case_id)
        else:
            return "Invalid user token"


    @endpoint("/get_decision_process", ["GET"], "application/json")    
    def get_decision_process(self, user_id, user_token, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            process = case_graph.value(case_id, orion_ns.decision_process)
            return process
        else:
            return "Invalid user token"
    
    
    @endpoint("/change_decision_process", ["POST"], "application/json")
    def change_decision_process(self, user_id, user_token, case_id, decision_process):
        """
        Changes the decision process url associated with a case.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            case_graph.set((case_id, orion_ns.decision_process, rdflib.Literal(decision_process)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"

    
    @endpoint("/change_case_property", ["POST"], "application/json")
    def change_case_property(self, user_id, token, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            case_graph.set((case_id, rdflib.URIRef(name), rdflib.Literal(value)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user or delegate token"

    
    @endpoint("/get_case_property", ["GET"], "application/json")
    def get_case_property(self, user_id, token, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            value = case_graph.value(case_id, rdflib.URIRef(name), None, None)
            return value
        else:
            return "Invalid user or delegate token"
        
    
    @endpoint("/get_decision_alternatives", ["GET"], "application/json")
    def get_decision_alternatives(self, user_id, token, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            q = "SELECT ?title ?a WHERE { ?case_id orion:alternative ?a . ?a orion:title ?title . }"
            result = case_graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "case_id": case_id })
            return list(result)
        else:
            return "Invalid user or delegate token"
    
    
    @endpoint("/change_alternative_property", ["POST"], "application/json")
    def change_alternative_property(self, user_id, token, case_id, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        if self.is_stakeholder_in_alternative(user_id, case_id, alternative) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                                                  self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            case_id = rdflib.URIRef(case_id)
            alternative = rdflib.URIRef(alternative)
            case_graph = self.graph.get_context(case_id)
            case_graph.set((alternative, rdflib.URIRef(name), rdflib.Literal(value)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user or delegate token"

    
    @endpoint("/get_alternative_property", ["GET"], "application/json")
    def get_alternative_property(self, user_id, token, case_id, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        if self.is_stakeholder_in_alternative(user_id, case_id, alternative) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                                                  self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            case_id = rdflib.URIRef(case_id)
            alternative = rdflib.URIRef(alternative)
            case_graph = self.graph.get_context(case_id)
            value = case_graph.value(alternative, rdflib.URIRef(name), None, None)
            return value
        else:
            return "Invalid user or delegate token"
        
        
    @endpoint("/get_ontology", ["GET", "POST"], "text/plain")
    def get_ontology(self, format):
        """
        Returns the base OWL ontology used by this case database. The base ontology may be extended by services.
        The format parameter indicates which serialization format should be used.
        """
        return self.ontology.serialize(format = format).decode("utf-8")
     
     
    @endpoint("/export_case_data", ["GET"], "application/json")
    def export_case_data(self, user_id, user_token, case_id, format):
        """
        Returns all data stored in the database concerning a specific case, with sufficient information to be able to
        restore an equivalent version of it. The format parameter indicates how the result should be returned.
        Here, "json" indicates a json-format which the knowledge repository for case data can import.
        All other format strings are passed on to a function in rdflib for creating RDF triples.
        
        TODO: It should be possible to set the level of detail on what gets exported.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            return case_graph.serialize(format = format).decode("utf-8")
        else:
            return "Invalid user token"
    
        
    #### NEW API FOR LINKED DATA #########################################################################
    
    def uri_to_id(self, uri):
        """
        Given a URI with the namespace used for the database followed by an id, return the id as an int.
        If the namespace is not a prefix of the uri, raise an exception.
        """
        if self.data_ns == uri[0 : len(self.data_ns)]:
            return int(uri[len(self.data_ns) : ])
        else:
            raise Exception("Wrong namespace: " + uri)
    
    
    def id_to_uri(self, resource_id):
        """
        Given a database id, return the corresponding URI.
        """
        return self.data_ns + str(resource_id)
    
    
    def new_uri(self):
        """
        Returns a new uri in the database namespace.
        """
        # Get the first free id and use it for the new uri, while increasing the id counter by one.
        case_db_term = rdflib.URIRef(self.data_ns + "case_db")
        id_counter_term = rdflib.URIRef(self.data_ns + "id_counter")
        id_counter = int(self.graph.value(case_db_term, id_counter_term, None, "0"))
        self.graph.remove((case_db_term, id_counter_term, None))
        self.graph.add((case_db_term, id_counter_term, rdflib.Literal(id_counter + 1)))
        self.graph.commit()
        return rdflib.URIRef(self.data_ns + str(id_counter))
    
    
    @endpoint("/get_data_namespace", ["GET", "POST"], "application/json")
    def get_data_namespace(self):
        """
        Returns the namespace used for data in this case database.
        """
        return self.data_ns
    
    
    @endpoint("/add_resource", ["POST"], "application/json")
    def add_resource(self, user_id, user_token, case_id, resource_class):
        """
        Adds a new resource of the given resource_class, and returns its generated URI.
        """

        # TODO: Add ontology and stakeholder checks.
        
        # A resource is stored in Neo4j as a node with the resource_class as a label.
        # The database id is used as the last part of the returned URI.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            orion_ns = rdflib.Namespace(self.orion_ns)
            uri = self.new_uri()
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.add((uri, rdflib.RDF.type, orion_ns[resource_class]))
            case_graph.commit()
            return uri
        else:
            return "Invalid user token"

    
    def add_resource_with_uri(self, resource_class, uri):
        """
        Adds a new resource of the given resource_class, where the uri is provided.
        If a node with the uri already exists, nothing is done.
        This is used to store relations to other namespaces in the database.
        It is only available internally in the CaseDB to set up elements from the ontology.
        """
        q = """MERGE (r:$class:$label { uri : { uri } } ) RETURN r"""
        result = self.query(q, { "class" : resource_class, "uri" : uri })

    
    @endpoint("/remove_resource", ["GET", "POST"], "application/json")
    def remove_resource(self, user_id, user_token, case_id, resource):
        """
        Removes a resource, and all properties to and from it.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            resource = rdflib.URIRef(resource)
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((resource, None, None))
            case_graph.remove((None, None, resource))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"

    
    @endpoint("/add_datatype_property", ["GET", "POST"], "application/json")
    def add_datatype_property(self, user_id, user_token, case_id, resource, property_name, value):
        """
        Adds value to resource under the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
        # A datatype property is stored in Neo4j as a node attribute.
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.add((rdflib.URIRef(resource), rdflib.URIRef(property_name), rdflib.Literal(value)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"
        
        
    @endpoint("/add_object_property", ["GET", "POST"], "application/json")
    def add_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        Relates resource1 to resource2 through the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.add((rdflib.URIRef(resource1), rdflib.URIRef(property_name), rdflib.URIRef(resource2)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"


    @endpoint("/get_datatype_property", ["GET", "POST"], "application/json")
    def get_datatype_property(self, user_id, user_token, case_id, resource, property_name):
        """
        Returns a value, for which there is a datatype property relation called property_name
        from the provided resource. 
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
#                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
        if (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token)):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            return case_graph.value(rdflib.URIRef(resource), rdflib.URIRef(property_name))
        else:
            return "Invalid user or delegate token"
        
        
    @endpoint("/get_object_properties", ["GET", "POST"], "application/json")
    def get_object_properties(self, user_id, user_token, case_id, resource, property_name):
        """
        Returns a list of resources, for which there is a datatype property relation called property_name
        from the provided resource. property_name is not given as a full uri, but just as the name.
        """

        # TODO: Add ontology and stakeholder checks.
        
        # Normally, we would get the uri of the resulting nodes. However, since it cannot assured that
        # all nodes have a uri, we get the node id instead and generate the uri from it.
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            return self.get_objects(user_id, user_token, case_id, resource, property_name)
        else:
            return "Invalid user token"


    @endpoint("/get_subjects", ["GET", "POST"], "application/json")
    def get_subjects(self, user_id, user_token, case_id, predicate, object):
        """
        Returns the subjects of all triples where the predicate and object are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.subjects(rdflib.URIRef(predicate), rdflib.URIRef(object))
            return list(result)


    @endpoint("/get_predicates", ["GET", "POST"], "application/json")
    def get_predicates(self, user_id, user_token, case_id, subject, object):
        """
        Returns the predicates of all triples where the subject and object are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.predicates(rdflib.URIRef(subject), rdflib.URIRef(object))
            return list(result)


    @endpoint("/get_objects", ["GET", "POST"], "application/json")
    def get_objects(self, user_id, user_token, case_id, subject, predicate):
        """
        Returns the subjects of all triples where the predicate and object are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.objects(rdflib.URIRef(subject), rdflib.URIRef(predicate))
            return list(result)


    @endpoint("/remove_datatype_property", ["GET", "POST"], "application/json")
    def remove_datatype_property(self, user_id, user_token, case_id, resource, property_name):
        """
        Remove all properties called property_name from the resource.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((rdflib.URIRef(resource), rdflib.URIRef(property_name), None))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"


    @endpoint("/remove_object_property", ["GET", "POST"], "application/json")
    def remove_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        Remove the object property relating resource1 to resource2.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((rdflib.URIRef(resource1), rdflib.URIRef(property_name), rdflib.URIRef(resource2)))
            case_graph.commit()
            return "Ok"
        else:
            return "Invalid user token"


    @endpoint("/toggle_object_property", ["GET", "POST"], "application/json")
    def toggle_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        If the triple (resource1, property_name, resource2) exists, it is deleted and False is returned. 
        Otherwise, it is added, and True is returned. The result thus reflects if the triple exists after the call.
        """
        
        # Read value from database here, then invert it!
        resource2 = rdflib.URIRef(resource2)
        props = self.get_objects(user_id = user_id, user_token = user_token, case_id = case_id, 
                                 subject = resource1, predicate = property_name)
        if resource2 in props:
            # Value is already set, so remove it
            self.remove_object_property(user_id = user_id, user_token = user_token, case_id = case_id,
                                        resource1 = resource1, property_name = property_name, resource2 = resource2)
            return False
        else:
            # Value is not set, so add id
            self.add_object_property(user_id = user_id, user_token = user_token, case_id = case_id, 
                                     resource1 = resource1, property_name = property_name, resource2 = resource2)
            return True