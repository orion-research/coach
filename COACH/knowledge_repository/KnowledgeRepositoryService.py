"""
Created on 13 juni 2016

@author: Jakob Axelsson

Knowledge repository for storing data about finished decision cases to use for guidance in new decision cases.
"""

# Standard libraries
import json
import os
import sys
import traceback
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import Microservice
from COACH.framework.coach import endpoint

from flask import request

# Database connection
from neo4j.v1 import GraphDatabase, basic_auth

# Semantic web framework
import rdflib
from rdflib.namespace import split_uri
import sqlalchemy
from rdflib_sqlalchemy.store import SQLAlchemy

class KnowledgeRepository:
    
    """
    Class implementing the KnowledgeRepository for storing data about finished decision cases.
    
    TODO: This class copies some generic methods for Neo4j access from CaseDB, probably should be a common base class instead.
    """
    
    def __init__(self, url, username, password):
        """
        Initiates the database at the provided url using the provided credentials.
        label indicates a label attached to all nodes used by this database, to distinguish them from nodes created by 
        other databases in the same DBMS.
        """
        self._db = GraphDatabase.driver("bolt://localhost", auth=basic_auth(username, password))
        self.ONTOLOGY_NAMESPACE = "http://www.orion-research.se/ontology#"

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
        
    def query(self, query, context = {}, session = None):
        """
        Function encapsulating the query interface to the database.
        q is the query string, and context is an optional dictionary containing variables to be substituted into q.
        If a session is provided, the query is executed in that session. Otherwise, a session is created, used
        for the query, and then closed again.
        """
        # Add the label to the context, so that it can be used in queries
        if session:
            return session.run(query, context)
        else:
            # If no session was provided, create one for this query and close it when done
            s = self.open_session()
            result = s.run(query, context)
            self.close_session(s)
            return result
        
    def export_case_to_KR(self, graph_description, format_):
        """
        Exports the data stored in the ontology graph to the Knowledge Repository database.
        """            
        try:
            case_graph = rdflib.Graph()
            case_graph.parse(data=graph_description, format=format_)
            session = self.open_session()
            
            for s, p, o in case_graph.triples((None, None, None)):
                
                if isinstance(s, rdflib.term.Literal):
                    raise RuntimeError("A subject must not be a Literal")
                
                predicate_name = split_uri(p)[1]
                if predicate_name == "type":
                    if not str(o).startswith(self.ONTOLOGY_NAMESPACE):
                        raise RuntimeError("The type of a node must be in the ontology namespace")
                    label = str(o)[len(self.ONTOLOGY_NAMESPACE):]
                    # Can not use a parameter for label, as it is not supported in neo4j
                    # TODO: Malicious code injection might be possible
                    query = "MERGE (node {uri: $uri}) SET node :" + label
                    self.query(query, {"uri": str(s)}, session)
                    continue
                    
                if isinstance(o, rdflib.Literal):
                    # Can not use the name of the property as a parameter, as it is not supported in neo4j
                    # TODO: Malicious code injection might be possible
                    query = "MERGE (node {uri: $uri}) SET node." + predicate_name + " = $value"
                    self.query(query, {"uri": str(s), "value":o.toPython()}, session)
                    continue
                
                query = """ MERGE (subject_node {uri: $subject_uri}) 
                            MERGE (object_node {uri: $object_uri})
                            MERGE (subject_node) -[:""" + predicate_name.upper() +"""]-> (object_node)
                        """
                self.query(query, {"subject_uri": str(s), "object_uri": str(o)}, session)

        except Exception as e:
            print(traceback.format_exc())
            raise e
        finally:
            self.close_session(session)
        
        
class KnowledgeRepositoryService(Microservice):

    """
    Implements the KR as a microservice with a web service interface.
    """

    def __init__(self, settings_file_name = None, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        # Initialize the graph database
        try:
            self.KR = KnowledgeRepository(self.get_setting("database"), 
                                          secret_data["neo4j_user_name"], 
                                          secret_data["neo4j_password"])
            
            self.ms.logger.info("Knowledge repository successfully connected")
        except:
            self.ms.logger.error("Fatal error: Knowledge repository cannot be accessed. Make sure that Neo4j is running!")

    @endpoint("/add_case", ["POST"], "application/json")    
    def add_case(self, description):
        """
        Endpoint for handling the addition of a new case to the KR.
        """
        self.KR.add_case(description)
        return "Ok"
    
    @endpoint("/export_case", ["GET"], "application/json")    
    def export_case(self, case_graph, format_):
        """
        Endpoint for handling the storage of a complete case to the KR.
        """
        self.KR.export_case_to_KR(case_graph, format_)
        return "Ok"
    
    