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

# Semantic web framework
import rdflib
from rdflib.namespace import split_uri
import sqlalchemy
from rdflib_sqlalchemy.store import SQLAlchemy

from flask import request

from collections import defaultdict


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

        # See http://docs.sqlalchemy.org/en/latest/dialects/sqlite.html#module-sqlalchemy.dialects.sqlite.pysqlite, under Connect strings
        self.db_uri = "sqlite:///" + filepath
        self.store = SQLAlchemy(identifier = ident, engine = sqlalchemy.create_engine(self.db_uri))
        self.graph = rdflib.ConjunctiveGraph(store = self.store, identifier = ident)
        
        # Store case database connection, using user_id and user_token as default parameters to all endpoint calls.
        self.kr_db_proxy = self.create_proxy(self.get_setting("knowledge_repository"))

        # Open the database file, creating it if it does not already exist.
        if not os.path.isfile(filepath):
            print("Creating new triple store at " + self.db_uri)
            self.store.open(rdflib.Literal(self.db_uri), create = True)
        else:
            print("Connected existing triple store at " + self.db_uri)
            self.store.open(rdflib.Literal(self.db_uri), create = False)

        self.orion_ns = "http://www.orion-research.se/ontology#"  # The name space for the ontology used
        self.data_ns = self.get_setting("protocol") + "://" + self.host + ":" + str(self.port) + "/data#"  # The namespace for this data source
        self.ns = { self.orion_ns : rdflib.Namespace(self.orion_ns),
                    self.data_ns : rdflib.Namespace(self.data_ns) }

        # Namespace objects cannot be stored as object attributes, since they collide with the microservice mechanisms
        orion_ns = rdflib.Namespace(self.orion_ns)
        data_ns = rdflib.Namespace(self.data_ns)

        ontology_context = orion_ns.ontology_context

        print("Contexts = " + str([c.identifier for c in self.graph.contexts()]))
        print("Ontology context = " + str(self.graph.get_context(ontology_context)))
        print("Number of statements in the database: " + str(len(self.graph)))
        #print("Namespaces in database: " + str([ns for ns in self.graph.namespaces()]))

        # Remove the ontology data, and reload it to ensure that it is updated to latest version
        self.ontology = self.graph.get_context(ontology_context)
        if self.ontology:
            print("Removing context triples from ontology")
            self.ontology.remove((None, None, None))
            print("Number of statements in the database after removing ontology: " + str(len(self.graph)))
            #print("Namespaces in database after removing ontology: " + str([ns for ns in self.graph.namespaces()]))
        else:
            print("Creating new ontology")
            self.ontology = rdflib.Graph(store = self.store, identifier = ontology_context)

        print("Loading new ontology data")
        ontology_path = os.path.join(self.working_directory, os.pardir, "Ontology.ttl")
        #print("Namespaces in ontology: " + str([ns for ns in self.ontology.namespaces()]))
        # An error message is produced when parsing, but the data is still read.
        # It appears to relate to the binding of namespaces in the ontology.
        # It could possibly be the addition of a default namespace when one already exists.
        self.ontology.parse(source = ontology_path, format = "ttl")
        print("Number of statements in the database after (re)loading ontology: " + str(len(self.graph)))
        #print("Namespaces in ontology after (re)loading: " + str([ns for ns in self.ontology.namespaces()]))

        
        self.ontology.bind("data", data_ns, override = True)
        self.ontology.bind("orion", orion_ns, override = True)
        

        print("Loaded " + self.orion_ns + " ontology with " + str(len(self.ontology)) + " statements")

        q = """SELECT ?c WHERE { ?c a orion:Case . }"""
        print("Sample query: Get all the cases in the database")
        qres = self.graph.query(q)
        for (a,) in qres:
            print(a)
    
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
        user_id = rdflib.URIRef(self.authentication_service_proxy.get_user_uri(user_id = user_id))
        result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                  initBindings = {"case_id": rdflib.URIRef(case_id), "user_id": user_id, "alternative": rdflib.URIRef(alternative)})
        return result


    @endpoint("/user_ids", ["POST"], "application/json")
    def user_ids(self, user_id, user_token):
        """
        Queries the case database and returns an iterable of all user ids (the name the user uses to log in).
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            # When using rdflib, the user is identified with an uri which consists of the authentication service url + user_id.
            return self.authentication_service_proxy.get_users()
        else:
            raise RuntimeError("Invalid user token")
         
    
    @endpoint("/user_cases", ["GET"], "application/json")
    def user_cases(self, user_id, user_token):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = "SELECT ?case_id ?case_title WHERE { ?case_id orion:role ?r . ?r orion:person ?user_uri . ?case_id orion:title ?case_title }"
            result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "user_uri": self.authentication_service_proxy.get_user_uri(user_id = user_id) })
            return list(result)
        else:
            raise RuntimeError("Invalid user token")
        
    
    @endpoint("/case_users", ["GET"], "application/json")
    def case_users(self, user_id, user_token, case_id):
        """
        Returns a list of ids of the users who are currently stakeholders in the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = "SELECT ?user_id WHERE { ?case_id orion:role ?r . ?r orion:person ?user_id . }"
            result = self.graph.query(q, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "case_id": case_id })
            return [u.toPython() for (u,) in result]
        else:
            raise RuntimeError("Invalid user token")        

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
            return str(case_id)
        else:
            raise RuntimeError("Invalid user token")        
    
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
            raise RuntimeError("Invalid user token")
           
    
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
            raise RuntimeError("Invalid user token")
        

    @endpoint("/add_stakeholder", ["POST"], "application/json")
    def add_stakeholder(self, user_id, user_token, case_id, stakeholder):
        """
        Adds a user as a stakeholder to the case. 
        """
        #TODO: Implements "if the user is already a stakeholder, nothing is changed" ?
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
            raise RuntimeError("Invalid user token")
        
    @endpoint("/change_stakeholder", ["POST"], "application/json")
    def change_stakeholder(self, user_id, user_token, case_id, role_property, stakeholder, values_list):  
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            orion_ns = rdflib.Namespace(self.orion_ns)
            
            query = """\
            SELECT ?role_uri
            WHERE {
                ?case_id orion:role ?role_uri .
                ?role_uri orion:person ?stakeholder_uri .
            }
            """
            query_result = case_graph.query(query, initNs={"orion": orion_ns},
                                            initBindings={"case_id": case_id, "stakeholder_uri": rdflib.URIRef(stakeholder)})
            if len(query_result) > 1 or len(query_result) == 0:
                raise RuntimeError("There must be exactly one role for the person " + str(stakeholder) + " but " +
                                   str(len(query_result)) + " were found.")
            
            role_uri = list(query_result)[0][0]
            role_property = rdflib.URIRef(role_property)
            case_graph.remove((role_uri, role_property, None))
            for value in values_list:
                case_graph.add((role_uri, role_property, rdflib.URIRef(value)))
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/get_stakeholder", ["GET"], "application/json")
    def get_stakeholder(self, user_id, user_token, case_id, role_properties_list):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):              
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            
            query = """\
            SELECT ?person_uri ?person_role
            WHERE {
                ?case_id orion:role ?role_uri .
                ?role_uri orion:person ?person_uri .
                ?role_uri ?role_property ?person_role .
            }
            """
            result = defaultdict(lambda: defaultdict(list))
            for role_property in role_properties_list:
                query_result = case_graph.query(query, initNs={"orion": orion_ns},
                                                initBindings={"case_id": case_id, "role_property": rdflib.URIRef(role_property)})
                
                for (person_uri, person_role) in query_result:
                    result[person_uri.toPython()][role_property].append(person_role.toPython())
                    
            return result
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/add_case_decision", ["POST"], "application/json")
    def add_case_decision(self, user_id, user_token, case_id, selected_alternative_uri, comments):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_id = rdflib.URIRef(case_id)
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_graph = self.graph.get_context(case_id)
            
            case_graph.set((case_id, orion_ns.comments, rdflib.Literal(comments)))
            case_graph.remove((case_id, orion_ns.selected_alternative, None))
            if selected_alternative_uri == "None":
                case_graph.add((case_id, orion_ns.selected_alternative, rdflib.Literal(selected_alternative_uri)))
                return
            
            case_graph.add((case_id, orion_ns.selected_alternative, rdflib.URIRef(selected_alternative_uri)))
        else:
            raise RuntimeError("Invalid user token")

    @endpoint("/add_alternative", ["POST"], "application/json")    
    def add_alternative(self, user_id, user_token, case_id, title, description, asset_characteristics):
        """
        Adds a decision alternative and links it to the case.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            
            query = " ASK WHERE {?case_id orion:alternative ?alternative_uri . ?alternative_uri orion:title ?alternative_name . }"
            query_result = case_graph.query(query, initNs={"orion": orion_ns},
                                            initBindings={"case_id": case_id, "alternative_name": rdflib.Literal(title)})
            if query_result.askAnswer:
                raise RuntimeError("An alternative with the name {0} already exists in the database".format(title))
            
            alternative = self.new_uri()
            case_graph.add((case_id, orion_ns.alternative, alternative))
            case_graph.add((alternative, rdflib.RDF.type, orion_ns.Alternative))
            
            case_graph.add((alternative, orion_ns.title, rdflib.Literal(title)))
            case_graph.add((alternative, orion_ns.description, rdflib.Literal(description)))
            for (predicate_name, value) in asset_characteristics:
                case_graph.add((alternative, orion_ns[predicate_name], rdflib.URIRef(value)))

            case_graph.commit()

            return str(case_id)
        else:
            raise RuntimeError("Invalid user token")
    
    @endpoint("/add_property", ["POST"], "application/json")
    def add_property(self, user_id, user_token, case_id, alternative_uri, property_ontology_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            
            property_uri = case_graph.value(None, orion_ns.ontology_id, property_ontology_id, None, False)
            if property_uri is None:
                property_uri = self.new_uri()
                case_graph.add((case_id, orion_ns.property, property_uri))
                case_graph.add((property_uri, rdflib.RDF.type, orion_ns.Property))
                case_graph.add((property_uri, orion_ns.ontology_id, rdflib.URIRef(property_ontology_id)))
                
            case_graph.add((property_uri, orion_ns.belong_to, rdflib.URIRef(alternative_uri)))
            
            case_graph.commit()
            return str(case_id)
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/add_estimation", ["POST"], "application/json")
    def add_estimation(self, user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id, value,
                       estimation_parameters, used_properties_to_estimation_method_ontology_id):
        #TODO: Make of this method a single transaction (included sub methods call), with rollback if an error occurred.
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):              
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            
            #Check whether an estimation has already been computed
            estimation_uri = self.get_estimation_uri(user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id)
            if estimation_uri is None:
                estimation_uri = self.new_uri()
                case_graph.add((case_id, orion_ns.estimation, estimation_uri))
                case_graph.add((estimation_uri, rdflib.RDF.type, orion_ns.Estimation))
                case_graph.add((estimation_uri, orion_ns.ontology_id, rdflib.URIRef(estimation_method_ontology_id)))
                case_graph.add((estimation_uri, orion_ns.belong_to_alternative, rdflib.URIRef(alternative_uri)))
                case_graph.add((estimation_uri, orion_ns.belong_to_property, rdflib.URIRef(property_uri)))
            
            case_graph.set((estimation_uri, orion_ns.value, rdflib.Literal(value)))
            self._add_estimation_parameters(case_id, estimation_uri, estimation_parameters)
            self._add_estimation_used_properties(user_id, user_token, case_id, alternative_uri, estimation_uri, 
                                                 used_properties_to_estimation_method_ontology_id)
            self._manage_estimation_up_to_date_property(case_id, estimation_uri)
            case_graph.commit()
            return str(case_id)
        else:
            raise RuntimeError("Invalid user token")
        
    def _add_estimation_parameters(self, case_id, estimation_uri, parameter_name_to_value_dict):
        query = """SELECT ?parameter ?parameter_name
        WHERE {
            ?case_id orion:parameter ?parameter .
            ?estimation orion:has_parameter ?parameter .
            ?parameter orion:name ?parameter_name
        }
        """
        case_id = rdflib.URIRef(case_id)
        estimation_uri = rdflib.URIRef(estimation_uri)
        result = self.graph.query(query, initNs = {"orion": rdflib.Namespace(self.orion_ns)},
                                  initBindings = {"case_id": case_id, "estimation": estimation_uri})
        parameter_name_to_uri_dict = {}
        for parameter_uri, parameter_name in result:
            parameter_name_to_uri_dict[parameter_name] = parameter_uri
        
        #Update parameter_name_to_value_dict so each key is changed to be a rdf literal
        for parameter_name in parameter_name_to_value_dict:
            parameter_name_to_value_dict[rdflib.Literal(parameter_name)] = parameter_name_to_value_dict.pop(parameter_name)
            
        case_graph = self.graph.get_context(case_id)
        orion_ns = rdflib.Namespace(self.orion_ns)
        for parameter_name in parameter_name_to_value_dict:
            if parameter_name not in parameter_name_to_uri_dict:
                parameter_uri = self.new_uri()
                case_graph.add((parameter_uri, rdflib.RDF.type, orion_ns.Parameter))
                case_graph.add((case_id, orion_ns.parameter, parameter_uri))
                case_graph.add((estimation_uri, orion_ns.has_parameter, parameter_uri))
                case_graph.add((parameter_uri, orion_ns.name, rdflib.Literal(parameter_name)))
            else:
                parameter_uri = rdflib.URIRef(parameter_name_to_uri_dict[parameter_name])
            
            value = rdflib.Literal(parameter_name_to_value_dict[parameter_name])
            case_graph.set((parameter_uri, orion_ns.value, value))
                    
        
    def _add_estimation_used_properties(self, user_id, user_token, case_id, alternative_uri, estimation_uri,
                                        used_properties_to_estimation_method_ontology_id):
        orion_ns = rdflib.Namespace(self.orion_ns)
        
        self.remove_datatype_property(user_id, user_token, case_id, estimation_uri, orion_ns.use_estimation)
        
        case_graph = self.graph.get_context(case_id)
        for property_uri in used_properties_to_estimation_method_ontology_id:
            used_estimation_uri = self.get_estimation_uri(user_id, user_token, case_id, alternative_uri, property_uri,
                                                          used_properties_to_estimation_method_ontology_id[property_uri])
            case_graph.add((estimation_uri, orion_ns.use_estimation, used_estimation_uri))
            
    @endpoint("/remove_estimation", ["POST"], "application/json")
    def remove_estimation(self, user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            estimation_uri = self.get_estimation_uri(user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id)
            if estimation_uri is None:
                return
            
            self._manage_estimation_up_to_date_property(case_id, estimation_uri)
            self._remove_estimation_parameters(user_id, user_token, case_id, estimation_uri)
            self.remove_resource(user_id, user_token, case_id, estimation_uri)
        else:
            raise RuntimeError("Invalid user token")
    
    def _remove_estimation_parameters(self, user_id, user_token, case_id, estimation_uri):
        query_parameters = """  SELECT ?parameter_uri
                                    WHERE {
                                        ?estimation_uri orion:has_parameter ?parameter_uri .
                                        ?case_id orion:parameter ?parameter_uri .
                                    }
                                """
        case_id = rdflib.URIRef(case_id)
        estimation_uri = rdflib.URIRef(estimation_uri)
        parameter_uri_list = list(self.graph.query(query_parameters, initNs = {"orion": rdflib.Namespace(self.orion_ns)},
                                                   initBindings = {"case_id": case_id, "estimation_uri": rdflib.URIRef(estimation_uri)}))
        for (parameter_uri,) in parameter_uri_list:
            self.remove_resource(user_id, user_token, case_id, parameter_uri)
            
    
    def _manage_estimation_up_to_date_property(self, case_id, estimation_uri):
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_graph = self.graph.get_context(case_id)
        
        dependents_estimation_uri_list = case_graph.subjects(orion_ns.use_estimation, estimation_uri)
        for dependent_estimation_uri in dependents_estimation_uri_list:
            case_graph.set((dependent_estimation_uri, orion_ns.up_to_date, rdflib.Literal(False)))
        case_graph.set((estimation_uri, orion_ns.up_to_date, rdflib.Literal(True)))
    
    @endpoint("/get_alternative_from_property_ontology_id", ["GET"], "application/json")
    def get_alternative_from_property_ontology_id(self, user_id, user_token, case_id, property_ontology_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            query = """SELECT ?alternative 
                        WHERE {
                            ?case_id orion:alternative ?alternative .
                            ?property orion:belong_to ?alternative .
                            ?property orion:ontology_id ?property_ontology_id
                        } 
                    """
            case_id = rdflib.URIRef(case_id)
            result = self.graph.query(query, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "property_ontology_id": property_ontology_id })
            return [a for (a,) in result]
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/get_estimation_uri", ["GET"], "application/json")
    def get_estimation_uri(self, user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            if property_uri is None:
                return None
            
            query = """SELECT ?estimation 
                        WHERE {
                            ?case_id orion:estimation ?estimation .
                            ?estimation orion:belong_to_alternative ?alternative_uri .
                            ?estimation orion:belong_to_property ?property .
                            ?estimation orion:ontology_id ?estimation_method_ontology_id
                        } 
                    """
            alternative_uri = rdflib.URIRef(alternative_uri)
            property_uri = rdflib.URIRef(property_uri)
            case_id = rdflib.URIRef(case_id)
            result = self.graph.query(query, initNs = { "orion": rdflib.Namespace(self.orion_ns)},
                                      initBindings = { "alternative_uri": alternative_uri, "property": property_uri, 
                                                      "estimation_method_ontology_id": estimation_method_ontology_id,
                                                      "case_id": case_id })
            result = [e for (e,) in result]
            if len(result) > 1:
                raise RuntimeError("At most one estimation should point to (alternative: " + str(alternative_uri) + ", property: " + 
                                   str(property_uri) + ", estimation method ontology id" + str(estimation_method_ontology_id) + 
                                   "), but " + str(len(result)) + " were found.")
            
            return result[0] if len(result) == 1 else None
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/get_estimation_value", ["GET"], "application/json")
    def get_estimation_value(self, user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id):
        """
        INPUT:
            alternative_uri: the uri of an alternative in the current database.
            property_uri: the uri of a property in the current database.
            estimation_method_ontology_id: the id of an estimation method in the ontology.
        OUTPUT:
            The triplet (alternative, property, estimation method's id) defined a unique estimation. If this estimation has previously
            been stored in the database, retrieved and returned a dictionary, with one property being the value of this estimation,
            and the other one a boolean telling whether the value is up-to-date or not. The keys are respectively "value" and
            "up_to_date". If no estimation are found, return None.
        """
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            estimation_uri = self.get_estimation_uri(user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id)
            if estimation_uri is None:
                return None
            
            orion_ns = rdflib.Namespace(self.orion_ns)
            estimation_value_list = self.get_objects(user_id, user_token, case_id, estimation_uri, orion_ns.value)
            if len(estimation_value_list) != 1:
                raise RuntimeError("There should be exactly one value for the estimation " + estimation_uri + " but " +
                                   str(len(estimation_value_list)) + " were found.")
            
            estimation_up_to_date_list = self.get_objects(user_id, user_token, case_id, estimation_uri, orion_ns.up_to_date)
            if len(estimation_up_to_date_list) != 1:
                raise RuntimeError("There should be exactly one up-to-date value for the estimation " + estimation_uri + " but " +
                                   str(len(estimation_up_to_date_list)) + " were found.")
            result = {"value": estimation_value_list[0].toPython(), "up_to_date": estimation_up_to_date_list[0].toPython()}
            return result
        else:
            raise RuntimeError("Invalid user token")
    
    @endpoint("/get_estimation_parameters", ["GET"], "application/json")
    def get_estimation_parameters(self, user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id):
        """
        INPUT:
            alternative_uri: the uri of an alternative in the current database.
            property_uri: the uri of a property in the current database.
            estimation_method_ontology_id: the id of an estimation method in the ontology.
        OUTPUT:
            A dictionary, in which the keys are the parameter's name of the estimation defined by the triplet 
            (alternative, property, estimation method's id), and the values are the value of the parameter.
            Return an empty dictionary if no estimation was found for the triplet (alternative, property, estimation method's id)
            or if no parameters exist for this estimation.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            estimation_uri = self.get_estimation_uri(user_id, user_token, case_id, alternative_uri, property_uri, estimation_method_ontology_id)
            if estimation_uri is None:
                return {}
            
            orion_ns = rdflib.Namespace(self.orion_ns)
            query = """SELECT ?parameter_name ?parameter_value
                        WHERE {
                            ?estimation_uri orion:has_parameter ?parameter .
                            ?parameter orion:value ?parameter_value .
                            ?parameter orion:name ?parameter_name
                        }
            """
            query_result = self.graph.query(query, initNs = {"orion": orion_ns}, initBindings = {"estimation_uri": estimation_uri})
            
            result = {}
            for (parameter_name, parameter_value) in query_result:
                result[parameter_name.toPython()] = parameter_value.toPython()
            return result
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/get_estimation_used_properties", ["GET"], "application/json")
    def get_estimation_used_properties(self, user_id, user_token, case_id, estimation_uri):
        """
        INPUT:
            estimation_uri: the uri of an estimation. It could be None
        OUTPUT:
            A dictionary with all the properties used by the provided estimation.
            The dictionary is from the property ontology's id to the estimation method ontology's id. 
            If the provided estimation_uri is None, return an empty dictionary.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            if estimation_uri is None:
                return {}
            orion_ns = rdflib.Namespace(self.orion_ns)
            query = """SELECT ?property_ontology_id ?estimation_method_ontology_id
                        WHERE {
                            ?estimation_uri orion:use_estimation ?used_estimation .
                            ?used_estimation orion:ontology_id  ?estimation_method_ontology_id .
                            ?used_estimation orion:belong_to_property ?property_uri .
                            ?property_uri orion:ontology_id ?property_ontology_id
                        }
            """
            query_result = self.graph.query(query, initNs = {"orion": orion_ns}, initBindings = {"estimation_uri": estimation_uri})
            
            result = {}
            for (property_ontology_id, estimation_method_ontology_id) in query_result:
                result[property_ontology_id.toPython()] = estimation_method_ontology_id.toPython()
            return result
        else:
            raise RuntimeError("Invalid user token")
    
    #TODO: To remove
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
            raise RuntimeError("Invalid user token")
    
    # TODO: to remove
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
            raise RuntimeError("Invalid user token")

    
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
            raise RuntimeError("Invalid user or delegate token")

    
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
            raise RuntimeError("Invalid user or delegate token")
    
    @endpoint("/get_general_context", ["GET"], "application/json")
    def get_general_context(self, user_id, user_token, case_id):
        if self.is_stakeholder(user_id, case_id) and self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_graph = self.graph.get_context(case_id)
            
            general_context_uri = case_graph.value(case_id, orion_ns.context, None, None)
            if general_context_uri is None:
                return ["", "", "", "", "", ""]
            
            result = []
            try:
                result.append(case_graph.value(general_context_uri, orion_ns.description, None, "").toPython())
            except AttributeError:
                result.append("")
                
            categories = [{"name": "organization", "general_id": "O00"},
                          {"name": "product", "general_id": "P00"},
                          {"name": "stakeholder", "general_id": "S00"},
                          {"name": "method", "general_id": "M00"},
                          {"name": "business", "general_id": "B00"},]
            
            query = """ SELECT ?general_category_value
                            WHERE {
                                ?general_context_uri ?predicate ?category_context_uri .
                                ?category_context_uri ?general_id ?entry_uri .
                                ?entry_uri orion:value ?general_category_value .
                            }
                """
                
            for category in categories:
                query_result = case_graph.query(query, initNs={"orion": orion_ns}, 
                                                initBindings={"general_context_uri": general_context_uri,
                                                              "predicate": orion_ns[category["name"]], 
                                                              "general_id": orion_ns[category["general_id"]]})
                query_result = [e for e in query_result]

                if len(query_result) > 1:
                    raise RuntimeError("There must be at most one value for the general description of the context " + category["name"])
                try:
                    result.append(query_result[0][0].toPython())
                except IndexError:
                    result.append("")
                    
            return result
        else:
            raise RuntimeError("Invalid user token")
    
    @endpoint("/save_general_context", ["POST"], "application/json")
    def save_general_context(self, user_id, user_token, case_id, general_context_list):
        if self.is_stakeholder(user_id, case_id) and self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            
            general_context_uri = case_graph.value(case_id, orion_ns.context, None, None)
            if general_context_uri is None:
                general_context_uri = self.new_uri()
                case_graph.add((case_id, orion_ns.context, general_context_uri))
            case_graph.set((general_context_uri, orion_ns.description, rdflib.Literal(general_context_list[0])))
            
            
            categories = [{"name": "organization", "general_id": "O00"},
                          {"name": "product", "general_id": "P00"},
                          {"name": "stakeholder", "general_id": "S00"},
                          {"name": "method", "general_id": "M00"},
                          {"name": "business", "general_id": "B00"},]
                
            for category, value in zip(categories, general_context_list[1:]):
                context_category_uri = case_graph.value(general_context_uri, orion_ns[category["name"]], None, None)
                if context_category_uri is None:
                    context_category_uri = self.new_uri()
                    case_graph.add((general_context_uri, orion_ns[category["name"]], context_category_uri))
                
                general_context_description_uri = case_graph.value(context_category_uri, orion_ns[category["general_id"]], None, None)
                if general_context_description_uri is None:
                    general_context_description_uri = self.new_uri()
                    case_graph.add((context_category_uri, orion_ns[category["general_id"]], general_context_description_uri))
                
                case_graph.set((general_context_description_uri, orion_ns.value, rdflib.Literal(value)))
        else:
            raise RuntimeError("Invalid user token")
        
        
    @endpoint("/save_context", ["POST"], "application/json")
    def save_context(self, user_id, user_token, case_id, context_predicate, context_values_dict):
        if self.is_stakeholder(user_id, case_id) and self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)

            orion_ns = rdflib.Namespace(self.orion_ns)
            general_context_uri = case_graph.value(case_id, orion_ns.context, None, None)
            if general_context_uri is None:
                general_context_uri = self.new_uri()
                case_graph.add((case_id, orion_ns.context, general_context_uri))
            
            context_uri = case_graph.value(general_context_uri, context_predicate, None, None)
            if context_uri is None:
                context_uri = self.new_uri()
                case_graph.add((general_context_uri, rdflib.URIRef(context_predicate), context_uri))
            else:
                entries = case_graph.predicate_objects(context_uri)
                for (_, entry) in entries:
                    case_graph.remove((entry, None, None))
                case_graph.remove((context_uri, None, None))                    
                    
            for entry_id in context_values_dict:
                for value in context_values_dict[entry_id]:
                    entry_uri = self.new_uri()
                    case_graph.add((context_uri, orion_ns[entry_id], entry_uri))
                    case_graph.add((entry_uri, orion_ns.value, rdflib.Literal(value)))
        else:
            raise RuntimeError("Invalid user token")

    @endpoint("/get_context", ["GET"], "application/json")
    def get_context(self, user_id, user_token, case_id, context_predicate):
        if self.is_stakeholder(user_id, case_id) and self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_id = rdflib.URIRef(case_id)
            case_graph = self.graph.get_context(case_id)
            orion_ns = rdflib.Namespace(self.orion_ns)

            query = """ SELECT ?entry_id ?entry_value
                        WHERE {
                            ?case_id orion:context ?general_context_uri .
                            ?general_context_uri ?context_predicate ?context_uri .
                            ?context_uri ?entry_id ?entry_uri .
                            ?entry_uri orion:value ?entry_value .
                        }
            """
            result_query = case_graph.query(query, initNs = {"orion": orion_ns}, 
                                            initBindings = {"case_id": case_id, "context_predicate": context_predicate})

            result = defaultdict(list)
            for (entry_id, entry_value) in result_query:
                entry_id = split_uri(entry_id)[1].upper()
                result[entry_id].append(entry_value.toPython())
            return result
        else:
            raise RuntimeError("Invalid user token")
    
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
            raise RuntimeError("Invalid user or delegate token")
    
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
            raise RuntimeError("Invalid user or delegate token")

    
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
            raise RuntimeError("Invalid user or delegate token")
        
        
    @endpoint("/get_ontology", ["GET", "POST"], "text/plain")
    def get_ontology(self, format_):
        """
        Returns the base OWL ontology used by this case database. The base ontology may be extended by services.
        The format parameter indicates which serialization format should be used.
        """
        return self.ontology.serialize(format = format_).decode("utf-8")
     
     
    @endpoint("/export_case_data", ["GET"], "application/json")
    def export_case_data(self, user_id, user_token, case_id, format_):
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
            return case_graph.serialize(format = format_).decode("utf-8")
        else:
            raise RuntimeError("Invalid user token")
    
    @endpoint("/is_case_in_database", ["GET"], "application/json")
    def is_case_in_database(self, user_id, user_token, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            query = " ASK WHERE { ?case_uri a orion:Case .} "
            query_result = self.graph.query(query, initNs={"orion": rdflib.Namespace(self.orion_ns)},
                                            initBindings={"case_uri": case_id})
            return query_result.askAnswer
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/import_case", ["POST"], "application/json")
    def import_case(self, user_id, user_token, graph_description, format_, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            case_graph = rdflib.Graph(store = self.store, identifier = rdflib.URIRef(case_id))
            case_graph.parse(data=graph_description, format=format_)
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/remove_case", ["GET", "POST"], "application/json")
    def remove_case(self, user_id, user_token, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(case_id)
            case_graph.remove((None, None, None))
        else:
            raise RuntimeError("Invalid user token")
    
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
        self.graph.set((case_db_term, id_counter_term, rdflib.Literal(id_counter + 1)))
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
            raise RuntimeError("Invalid user token")
    
    @endpoint("/remove_resource", ["GET", "POST"], "application/json")
    def remove_resource(self, user_id, user_token, case_id, resource):
        """
        Removes a resource, and all properties to and from it.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            resource = rdflib.URIRef(resource)
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((resource, None, None))
            case_graph.remove((None, None, resource))
            case_graph.commit()
            return "Ok"
        else:
            raise RuntimeError("Invalid user token")

    
    @endpoint("/add_datatype_property", ["GET", "POST"], "application/json")
    def add_datatype_property(self, user_id, user_token, case_id, resource, property_name, value):
        """
        Adds value to resource under the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.add((rdflib.URIRef(resource), rdflib.URIRef(property_name), rdflib.Literal(value)))
            case_graph.commit()
            return "Ok"
        else:
            raise RuntimeError("Invalid user token")
        
        
    @endpoint("/add_object_property", ["GET", "POST"], "application/json")
    def add_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        Relates resource1 to resource2 through the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.add((rdflib.URIRef(resource1), rdflib.URIRef(property_name), rdflib.URIRef(resource2)))
            case_graph.commit()
            return "Ok"
        else:
            raise RuntimeError("Invalid user token")

    @endpoint("/get_subjects", ["GET", "POST"], "application/json")
    def get_subjects(self, user_id, user_token, case_id, predicate, object_):
        """
        Returns the subjects of all triples where the predicate and object_ are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.subjects(rdflib.URIRef(predicate), rdflib.URIRef(object_))
            return list(result)
        else:
            raise RuntimeError("Invalid user token")


    @endpoint("/get_predicates", ["GET", "POST"], "application/json")
    def get_predicates(self, user_id, user_token, case_id, subject, object_):
        """
        Returns the predicates of all triples where the subject and object are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.predicates(rdflib.URIRef(subject), rdflib.URIRef(object_))
            return list(result)
        else:
            raise RuntimeError("Invalid user token")


    @endpoint("/get_objects", ["GET", "POST"], "application/json")
    def get_objects(self, user_id, user_token, case_id, subject, predicate):
        """
        Returns the objects of all triples where the subject and predicate are as provided.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            result = case_graph.objects(rdflib.URIRef(subject), rdflib.URIRef(predicate))
            return list(result)
        else:
            raise RuntimeError("Invalid user token")
        
    @endpoint("/get_value", ["GET", "POST"], "application/json")
    def get_value(self, user_id, user_token, case_id, subject, predicate, object_, default_value=None, any_=True):
        """
        DESCRIPTION:
            Get a value for a pair of two criteria among subject, predicate and object_.
        INPUT:
            user_id, user_token: The identifier of a user. They are used to check the authenticity of the caller.
            case_id: The uri of the case on which the value will be retrieved. The user must be a stakeholder of this case.
            subject, predicate, object_: Exactly one of those must be None. The two provided values are used to retrieve the missing one.
                The values do not need to be rdf term.
            default_value: If no value is found, return this value instead.
            any_: If True, return any value in the case there is more than one, else, raise UniquenessError
        OUTPUT:
            The missing value among subject, predicate, object_. If there is no value corresponding to the two provided criteria, the 
            default_value is returned instead. If there is more than one value corresponding to the two provided criteria and any_ is True,
            return any value among them.
        ERROR:
            Raise RuntimeError if the user_token does not match the user_id.
            Raise UniquenessError if there is more than one value matching the provided criteria and any_ is False
            Raise an error if subject, predicate and object_ are all defined. 
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            if subject is not None:
                subject = rdflib.URIRef(subject)
            if predicate is not None:
                predicate = rdflib.URIRef(predicate)
                
            if object_ is None:
                return case_graph.value(subject, predicate, None, default_value, any_)
            else:
                value_with_literal_object = case_graph.value(subject, predicate, rdflib.Literal(object_), default_value, any_)
                if value_with_literal_object == default_value:
                    return case_graph.value(subject, predicate, rdflib.URIRef(object_), default_value, any_)
                else:
                    return value_with_literal_object
        else:
            raise RuntimeError("Invalid user token")


    @endpoint("/remove_datatype_property", ["GET", "POST"], "application/json")
    def remove_datatype_property(self, user_id, user_token, case_id, resource, property_name):
        """
        Remove all properties called property_name from the resource.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((rdflib.URIRef(resource), rdflib.URIRef(property_name), None))
            case_graph.commit()
            return "Ok"
        else:
            raise RuntimeError("Invalid user token")


    @endpoint("/remove_object_property", ["GET", "POST"], "application/json")
    def remove_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        Remove the object property relating resource1 to resource2.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            case_graph.remove((rdflib.URIRef(resource1), rdflib.URIRef(property_name), rdflib.URIRef(resource2)))
            case_graph.remove((rdflib.URIRef(resource1), rdflib.URIRef(property_name), rdflib.Literal(resource2)))
            case_graph.commit()
            return "Ok"
        else:
            raise RuntimeError("Invalid user token")


    @endpoint("/toggle_object_property", ["GET", "POST"], "application/json")
    def toggle_object_property(self, user_id, user_token, case_id, resource1, property_name, resource2):
        """
        If the triple (resource1, property_name, resource2) exists, it is deleted and False is returned. 
        Otherwise, it is added, and True is returned. The result thus reflects if the triple exists after the call.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            case_graph = self.graph.get_context(rdflib.URIRef(case_id))
            resource1 = rdflib.URIRef(resource1)
            predicate = rdflib.URIRef(property_name)
            resource2 = rdflib.URIRef(resource2)
            
            if resource2 in case_graph.objects(resource1, property_name):
                case_graph.remove((resource1, predicate, resource2))
                return False
            else:
                case_graph.add((resource1, predicate, resource2))
                return True
        else:
            raise RuntimeError("Invalid user token")
            
            
            
            