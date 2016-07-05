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
        
    
    def add_case(self, case_description):
        """
        Adds a case to the KR from a description provided as a json string.
        
        NOTES: This is just a stub, it should go through the description and add it to the KR on its internal format
        using Neo4j queries.
        - if a case already exists its information is updated
        - the addition is done in pieces without exploiting a proper transaction
        """
        # Retrieves case data from JSON format
        c_descr = json.loads(case_description)
        # Retrieves case node attributes and writes them into the KR. Then it retrieves the case_id
        case_node = c_descr.get('case')
        node_properties = case_node.get('properties')
        q = """\
        MERGE (c:Case:{label} {{id: "{case_node[id]}"}})
        SET c.title = "{node_properties[title]}", c.description = "{node_properties[description]}" 
        RETURN id(c) AS case_id"""
        case_id = next(iter(self.query(q, locals())))["case_id"]
        # Retrieves stakeholders information
        c_stakeholders = c_descr.get('stakeholders')
        # Stores stakeholders data into the KR
        self.add_stakeholders(case_id, c_stakeholders)
        
        
    def asset_origins(self):
        """
        Queries the knowledge repository database and returns an iterable of all asset origins options.
        """
        q = """MATCH (ao:Origin:{label}) RETURN ao.name AS asset_origin"""
        return [result["asset_origin"] for result in self.query(q, locals())]
    
    
    def add_stakeholders(self, c_id, c_stakeholders):
        """
        Adds stakeholders to the case c_id.
        
        NOTES:
        - the decision role of the stakeholder is added as a property of the stakeholder relationship
        - the stakeholder is named with her user_id
        - a stakeholder with multiple decision roles and/or involvement in multiple decisions is not duplicated
        """
        s = self.open_session()
        # Iterate over the list elements and get appropriate attributes
        for l_idx in range(len(c_stakeholders)):
            s_id = c_stakeholders[l_idx].get('id')
            s_prop = c_stakeholders[l_idx].get('properties')
            role = c_stakeholders[l_idx].get('role')
            # Create a new stakeholder, and get it's id
            q1 = """MERGE (s:Stakeholder:{label} {{id: "{s_id}", name: "{s_prop[user_id]}"}}) RETURN id(s) AS sh_id"""
            new_stakeholder = next(iter(self.query(q1, locals(), s)))["sh_id"]
        
            # Creates a corresponding new stakeholder relationship
            q2 = """\
            MATCH (c:Case:{label}), (ns:Stakeholder:{label})
            WHERE id(c) = {c_id} AND id(ns) = {new_stakeholder}
            MERGE (c) -[r:Stakeholder]-> (ns)
            ON CREATE SET r.role = "{role}"
            """
            self.query(q2, locals(), s)
        self.close_session(s)
        
        
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