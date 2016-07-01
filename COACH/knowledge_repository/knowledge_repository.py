"""
Created on 13 juni 2016

@author: Jakob Axelsson

Knowledge repository for storing data about finished decision cases to use for guidance in new decision cases.
"""

# Standard libraries
import json
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import Microservice

from flask import request

# Database connection
from neo4j.v1 import GraphDatabase, basic_auth


class KnowledgeRepository:
    
    """
    Class implementing the KnowledgeRepository for storing data about finished decision cases.
    
    TODO: This class copies some generic methods for Neo4j access from CaseDB, probably should be a common base class instead.
    """
    
    def __init__(self, url, username, password, label):
        """
        Initiates the database at the provided url using the provided credentials.
        label indicates a label attached to all nodes used by this database, to distinguish them from nodes created by 
        other databases in the same DBMS.
        """
        self._db = GraphDatabase.driver("bolt://localhost", auth=basic_auth(username, password))
        self.label = label


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
        q is the query string, and context is an optional dictionary containing variables to be substituted into q.
        If a session is provided, the query is executed in that session. Otherwise, a session is created, used
        for the query, and then closed again.
        """
        # Add the label to the context, so that it can be used in queries
        context["label"] = self.label
        if session:
            return session.run(q.format(**context))
        else:
            # If no session was provided, create one for this query and close it when done
            s = self.open_session()
            result = s.run(q.format(**context))
            self.close_session(s)
            return result
        

    def asset_origins(self):
        """
        Queries the knowledge repository database and returns an iterable of all asset origins options.
        """
        q = """MATCH (ao:Origin:{label}) RETURN ao.name AS asset_origin"""
        return [result["asset_origin"] for result in self.query(q, locals())]
    
    
    def add_case(self, case_description):
        """
        Adds a case to the KR from a description provided as a json string.
        
        TODO: This is just a stub, it should go through the description and add it to the KR on its internal format
        using Neo4j queries.
        """
        return
        
        
class KnowledgeRepositoryService(Microservice):

    """
    Implements the KR as a microservice with a web service interface.
    """

    def __init__(self, settings_file_name, secret_data_file_name, handling_class = None, working_directory = None):
        super().__init__(settings_file_name, handling_class = handling_class, working_directory = working_directory)

        # Read secret data file
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        # Initialize the graph database
        try:
            self.KR = KnowledgeRepository(self.get_setting("database"), 
                                          secret_data["neo4j_user_name"], 
                                          secret_data["neo4j_password"],
                                          "KR")
            self.ms.logger.info("Knowledge repository successfully connected")
        except:
            self.ms.logger.error("Fatal error: Knowledge repository cannot be accessed. Make sure that Neo4j is running!")

            
    def create_endpoints(self):
        """
        Initialize the API as web service endpoints.
        """
        self.ms.add_url_rule("/add_case", view_func = self.add_case, methods = ["POST"])
        
        
    def add_case(self):
        """
        Endpoint for handling the addition of a new case to the KR.
        """
        self.KR.add_case(request.values.get("description"))
        return "Ok"
