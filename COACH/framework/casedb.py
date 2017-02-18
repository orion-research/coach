'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from flask import Response

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Standard libraries
import json
from string import Template

# Database connection
from neo4j.v1 import GraphDatabase, basic_auth


class CaseDatabase(coach.Microservice):
    
    """
    The case database provides the interface to the database for storing case information. 
    It wraps an API around a standard graph DBMS.
    
    TODO: 
    - All actions should generate entries into a history, showing who, when, and what has been done.
    This is useful for being able to analyze decision processes. 
    """

    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initiates the database at the provided url using the provided credentials.
        label indicates a label attached to all nodes used by this database, to distinguish them from nodes created by 
        other databases in the same DBMS.
        """
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)

        self.root_service_url = self.get_setting("protocol") + "://" + self.get_setting("host") + ":" + str(self.get_setting("port"))

        self.label = self.get_setting("label")
        
        # Store authentication service connection
        self.authentication_service_proxy = self.create_proxy(self.get_setting("authentication_service"))

        # Initiate neo4j
        try:
            self._db = GraphDatabase.driver("bolt://localhost", 
                                            auth=basic_auth(secret_data["neo4j_user_name"], 
                                                            secret_data["neo4j_password"]))
            self.ms.logger.info("Case database successfully connected")
            print("Case database successfully connected")
        except:
            self.ms.logger.error("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")
            print("Fatal error: Case database cannot be accessed. Make sure that Neo4j is running!")
    
    
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
        q is the query string, and context is an optional dictionary containing parameters to be substituted into q.
        If a session is provided, the query is executed in that session. Otherwise, a session is created, used
        for the query, and then closed again.
        """
        try:
            # Add the label to the context, so that it can be used in queries
            context["label"] = self.label
            # Build query string by substituting template parameters with their context values
            q = Template(q).substitute(**context)
            if session:
                return session.run(q, context)
            else:
                # If no session was provided, create one for this query and close it when done
                s = self.open_session()
                result = s.run(q, context)
                self.close_session(s)
                return result
        except Exception as e:
            print("Error in Case Database query: " + str(e))


    def is_stakeholder(self, user_id, case_id):
        """
        Returns true if user_id is a stakeholder in case_id.
        """
        q = """\
        MATCH (case:Case:$label) -[:Stakeholder]-> (user:User:$label {user_id: {user_id}}) 
        RETURN id(case) AS id"""
        params = { "user_id": user_id }
        return int(case_id) in [result["id"] for result in self.query(q, params)]


    def is_stakeholder_in_alternative(self, user_id, case_id, alternative):
        """
        Returns true if alternative is linked to a case where the user_id is a stakeholder.
        """
        q = """\
        MATCH (case:Case:$label) -[:Stakeholder]-> (user:User:$label {user_id: {user_id}}) 
        MATCH (case:Case:$label) -[:Alternative]-> (alt:Alternative:$label)
        WHERE id(alt) = {alt_id}
        RETURN id(case) AS id"""
        params = { "user_id": user_id, "alt_id": int(alternative) }
        return int(case_id) in [result["id"] for result in self.query(q, params)]


    @endpoint("/user_ids", ["POST"])
    def user_ids(self, user_id, user_token):
        """
        Queries the case database and returns an iterable of all user ids (the name the user uses to log in).
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MATCH (u:User:$label) RETURN u.user_id AS user_id"""
            return Response(json.dumps([result["user_id"] for result in self.query(q)]))
        else:
            return Response("Invalid user token")
         
    
    @endpoint("/user_cases", ["GET"])
    def user_cases(self, user_id, user_token):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """\
            MATCH (case:Case:$label) -[:Stakeholder]-> (user:$label {user_id: {user_id}}) 
            RETURN id(case) AS id, case.title AS title"""
            params = { "user_id": user_id }
            return Response(json.dumps([(result["id"], result["title"]) for result in self.query(q, params)]))
        else:
            return Response("Invalid user token")
        
    
    @endpoint("/create_user", ["POST"])
    def create_user(self, user_id, user_token):
        """
        Creates a new user in the database, if it is not already there. 
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MERGE (u:User:$label {user_id : {user_id}})"""
            params = { "user_id": user_id }
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")
        

    @endpoint("/create_case", ["POST"])
    def create_case(self, title, description, initiator, user_token):
        """
        Creates a new case in the database, with a relation to the initiating user (referenced by user_id). 
        It returns the database id of the new case.
        """

        if self.authentication_service_proxy.check_user_token(user_id = initiator, user_token = user_token):
            s = self.open_session()
            # First create the new case node, and get it's id
            q1 = """CREATE (c:Case:$label {title: {title}, description: {description}}) RETURN id(c) AS case_id"""
            params1 = { "title": title, "description": description }
            case_id = int(self.query(q1, params1, s).single()["case_id"])
            
            # Then create the relationship
            q2 = """\
            MATCH (c:Case:$label), (u:User:$label)
            WHERE id(c) = {case_id} AND u.user_id = {initiator}
            CREATE (c) -[:Stakeholder {role: "initiator"}]-> (u)
            """
            params2 = { "case_id": case_id, "initiator": initiator }
            self.query(q2, params2, s)
            self.close_session(s)
            return Response(json.dumps(case_id))        
        else:
            return Response("Invalid user token")
        
    
    @endpoint("/change_case_description", ["POST"])
    def change_case_description(self, user_id, user_token, case_id, title, description):
        """
        Changes the title and description fields of the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} SET case.title = {title}, case.description = {description}"""
            params = { "case_id": int(case_id), "title": title, "description": description}
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")
           
    
    @endpoint("/get_case_description", ["GET"])    
    def get_case_description(self, user_id, user_token, case_id):
        """
        Returns a tuple containing the case title and description for the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} RETURN case.title AS title, case.description AS description"""
            params = { "case_id": int(case_id) }
            result = self.query(q, params).single()
            return Response(json.dumps((result["title"], result["description"])))
        else:
            return Response("Invalid user token")
        

    @endpoint("/add_stakeholder", ["POST"])
    def add_stakeholder(self, user_id, user_token, case_id, stakeholder, role):
        """
        Adds a user as a stakeholder with the provided role to the case. 
        If the user is already a stakeholder, nothing is changed. 
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            q = """\
            MATCH (c:Case:$label), (u:User:$label)
            WHERE id(c) = {case_id} AND u.user_id = {user_id}
            MERGE (c) -[r:Stakeholder]-> (u)
            ON CREATE SET r.role = {role}
            """
            params = { "user_id": stakeholder, "case_id": int(case_id), "role": role}
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")


    @endpoint("/add_alternative", ["POST"])    
    def add_alternative(self, user_id, user_token, title, description, case_id):
        """
        Adds a decision alternative and links it to the case.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            s = self.open_session()
            # First create the new alternative, and get it's id
            q1 = """CREATE (a:Alternative:$label {title: {title}, description: {description}}) RETURN id(a) AS alt_id"""
            params1 = { "title": title, "description": description, "case_id": int(case_id) }
            new_alternative = int(self.query(q1, params1, s).single()["alt_id"])
            
            # Then create the relationship to the case
            q2 = """\
            MATCH (c:Case:$label), (a:Alternative:$label)
            WHERE id(c) = {case_id} AND id(a) = {new_alternative}
            CREATE (c) -[:Alternative]-> (a)
            """
            params2 = { "new_alternative": new_alternative, "case_id": int(case_id)}
            self.query(q2, params2, s)
            self.close_session(s)
            return Response(str(case_id))        
        else:
            return Response("Invalid user token")


    @endpoint("/get_decision_process", ["GET"])    
    def get_decision_process(self, user_id, user_token, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            try:
                q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} RETURN case.decision_process AS process LIMIT 1"""
                params = { "case_id": int(case_id)}
                return Response(json.dumps(self.query(q, params).single()["process"]))
            except:
                return Response(json.dumps(None))
        else:
            return Response("Invalid user token")
    
    
    @endpoint("/change_decision_process", ["POST"])
    def change_decision_process(self, user_id, user_token, case_id, decision_process):
        """
        Changes the decision process url associated with a case.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} SET case.decision_process = {decision_process}"""
            params = { "case_id": int(case_id), "decision_process": decision_process}
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")

    
    @endpoint("/change_case_property", ["POST"])
    def change_case_property(self, user_id, token, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} SET case.$name = {value}"""
            params = { "case_id": int(case_id), "value": value, "name": name}
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user or delegate token")

    
    @endpoint("/get_case_property", ["GET"])
    def get_case_property(self, user_id, token, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            try:
                q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} RETURN case.$name AS name"""
                params = { "case_id": int(case_id), "name": name }
                query_result = self.query(q, params).single()["name"]
                return Response(json.dumps(query_result))
            except:
                return Response(json.dumps(None))
        else:
            return Response("Invalid user or delegate token")
        
    
    @endpoint("/get_decision_alternatives", ["GET"])
    def get_decision_alternatives(self, user_id, token, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        """
        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            q = """\
            MATCH (case:Case:$label) -[:Alternative]-> (alt:Alternative:$label) 
            WHERE id(case) = {case_id} 
            RETURN alt.title AS title, id(alt) AS alt_id"""
            params = { "case_id": int(case_id) }
            alternatives = [(result["title"], result["alt_id"]) for result in self.query(q, params)]
            return Response(json.dumps(alternatives))
        else:
            return Response("Invalid user or delegate token")
    
    
    @endpoint("/change_alternative_property", ["POST"])
    def change_alternative_property(self, user_id, token, case_id, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        if self.is_stakeholder_in_alternative(user_id, case_id, alternative) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                                                  self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            q = """MATCH (alt:Alternative:$label) WHERE id(alt) = {alternative} SET alt.$name = {value}"""
            params = { "alternative": int(alternative), "value": value, "name": name }
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user or delegate token")

    
    @endpoint("/get_alternative_property", ["GET"])
    def get_alternative_property(self, user_id, token, case_id, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        if self.is_stakeholder_in_alternative(user_id, case_id, alternative) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
                                                                                  self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
            try:
                q = """MATCH (alt:Alternative:$label) WHERE id(alt) = {alternative} RETURN alt.$name AS name"""
                params = { "alternative": int(alternative), "name": name }
                query_result = self.query(q, params).single()["name"]
                return Response(json.dumps(query_result))
            except:
                return Response(json.dumps(None))
        else:
            return Response("Invalid user or delegate token")
        
    
    @endpoint("/export_case_data", ["GET"])
    def export_case_data(self, user_id, user_token, case_id):
        """
        Returns all data stored in the database concerning a specific case, with sufficient information to be able to
        restore an equivalent version of it.
        
        TODO: It should be possible to set the level of detail on what gets exported.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            graph = dict()
    
            # Get case node
            q = """MATCH (case:Case:$label) WHERE id(case) = {case_id} RETURN case"""
            params = { "case_id": int(case_id)}
            case_node = self.query(q, params).single()["case"]
            graph["case"] = {"id" : case_node.id, "properties": case_node.properties}
            
            # Get stakeholders and their roles
            q = """MATCH (case:Case:$label) -[role:Stakeholder]-> (user:$label)
                   WHERE id(case) = {case_id}
                   RETURN user, role"""
            graph["stakeholders"] = [{"id": result["user"].id, "properties": result["user"].properties, "role": result["role"].properties["role"]}
                                     for result in self.query(q, params)]
    
            # Get alternatives
            q = """MATCH (case:Case:$label) -[:Alternative]-> (alt:Alternative:$label) 
                   WHERE id(case) = {case_id} 
                   RETURN alt"""
            graph["alternatives"] = [{"id": result["alt"].id, "properties": result["alt"].properties}
                                     for result in self.query(q, params)]
            
            # Return graph as json
            return Response(json.dumps(graph, indent = 4))
        else:
            return Response("Invalid user token")    