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

# Semantic web framework
import rdflib


class CaseDatabase(coach.GraphDatabaseService):
    
    """
    The case database provides the interface to the database for storing case information. 
    It wraps an API around a standard graph DBMS.
    
    TODO: 
    - All actions should generate entries into a history, showing who, when, and what has been done.
    This is useful for being able to analyze decision processes. 
    """

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
        
    
    @endpoint("/case_users", ["GET"])
    def case_users(self, user_id, user_token, case_id):
        """
        Returns a list of ids of the users who are currently stakeholders in the case with case_id.
        """
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """\
            MATCH (case:Case:$label) -[:Stakeholder]-> (user:$label) 
            WHERE id(case) = {case_id}
            RETURN user.user_id AS user_id"""
            params = { "case_id": int(case_id) }
            return Response(json.dumps([result["user_id"] for result in self.query(q, params)]))
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
        
        
    @endpoint("/get_ontology", ["GET", "POST"])
    def get_ontology(self, format):
        """
        Returns the base OWL ontology used by this case database. The base ontology may be extended by services.
        The format parameter indicates which serialization format should be used.
        """
        # Create the name spaces
        owl = rdflib.OWL
        rdf = rdflib.RDF
        rdfs = rdflib.RDFS
        xsd = rdflib.XSD
        orion = rdflib.Namespace("https://github.com/orion-research/coach/tree/master/COACH/ontology#")  # The name space for the ontology used
        
        # Create the graph and bind the name spaces    
        ontology = rdflib.ConjunctiveGraph()
        ontology.bind("orion", orion)
                
        triples = [
            # Define the attribute types id, title
            (orion.id, rdf.type, owl.DatatypeProperty),
            (orion.id, rdfs.range, xsd.positiveInteger),
            
            (orion.title, rdf.type, owl.DatatypeProperty),
            (orion.title, rdfs.range, xsd.string),
                
            # Define Case class and attributes id, title, ... (more to be added)
            (orion.Case, rdf.type, owl.Class),
            (orion.id, rdfs.domain, orion.Case),
            (orion.title, rdfs.domain, orion.Case),
            
            # Define User class and attributes id, user_id
            (orion.User, rdf.type, owl.Class),
            (orion.id, rdfs.domain, orion.User),

            (orion.user_id, rdf.type, owl.DatatypeProperty),
            (orion.user_id, rdfs.domain, orion.User),
            (orion.user_id, rdfs.range, xsd.string),
                             
            # Define Alternative class and attributes id, title, ... (more to be added)
            (orion.Alternative, rdf.type, owl.Class),       
            (orion.id, rdfs.domain, orion.Alternative),
            
            # Define Stakeholder_in class and attribute role
            (orion.Stakeholder_in, rdf.type, owl.Class),       
            (orion.role, rdf.type, owl.DatatypeProperty),
            (orion.role, rdfs.domain, orion.Stakeholder),
            (orion.role, rdfs.range, xsd.string)
        ]
        for t in triples:
            ontology.add(t)
        
        # Serialize the ontology graph
        return Response(json.dumps(ontology.serialize(format = format).decode("utf-8")))
     
     
    @endpoint("/export_case_data", ["GET"])
    def export_case_data(self, user_id, user_token, case_id, format):
        """
        Returns all data stored in the database concerning a specific case, with sufficient information to be able to
        restore an equivalent version of it. The format parameter indicates how the result should be returned.
        Here, "json" indicates a json-format which the knowledge repository for case data can import.
        All other format strings are passed on to a function in rdflib for creating RDF triples.
        
        TODO: It should be possible to set the level of detail on what gets exported.
        """

        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
            # Build the graph as a dictionary based tree
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

            # Serialize the graph on an appropriate format
            if format == "json":
                # Serialize graph as json
                return Response(json.dumps(graph, indent = 4))
            else:
                (nodes, edges, properties, labels) = self.get_graph_starting_in_node(int(case_id))

                # Serialize case data as RDF triples by transforming graph to an rdflib graph, and then serialize it using the formats provided in the rdflib.

                # Create the name spaces
                ns = rdflib.Namespace(self.host + "/#")  # The name space for this data source
                orion = rdflib.Namespace("https://github.com/orion-research/coach/tree/master/COACH/ontology#")  # The name space for the ontology used
                rdf = rdflib.RDF

                # Create the graph and bind the name spaces    
                rdfgraph = rdflib.ConjunctiveGraph()
                rdfgraph.bind("ns", ns)
                rdfgraph.bind("orion", orion)
                
                # TODO: Rewrite the below using the case_graph data from above.
                # Add the node ids and types
                for n in nodes:
                    # Add node id
                    rdfgraph.add((ns.node + str(n), orion.id, rdflib.Literal(str(n))))
                    # Add node type
                    rdfgraph.add((ns.node + str(n), rdf.type, orion[labels[n]]))
                    # Add node properties
                    for (p, v) in properties[n].items():
                        rdfgraph.add((ns.node + str(n), orion[p], rdflib.Literal(v)))

                # Add the edge node ids and types
                for (n1, e, n2) in edges:
                    if e in properties:
                        # If the edge has properties, it has to be represented as a node in the triples
                        # Add edge id
                        rdfgraph.add((ns.node + str(e), orion.id, rdflib.Literal(str(e))))
                        # Add edge type
                        rdfgraph.add((ns.node + str(e), rdf.type, orion[labels[e]]))
                        # Add edge properties
                        for (p, v) in properties[e].items():
                            rdfgraph.add((ns.node + str(e), orion[p], rdflib.Literal(v)))
                        # Add edge relations
                        rdfgraph.add((ns.node + str(e), orion[labels[n1].lower()], ns.node + str(n1)))
                        rdfgraph.add((ns.node + str(e), orion[labels[n2].lower()], ns.node + str(n2)))
                    else:
                        # If the edge has no properties, there is no need to create a node for it
                        rdfgraph.add((ns.node + str(n1), orion[labels[e]], ns.node + str(n2)))
                
                # OLD:
                """
                # Add the case node and its properties
                case_node = ns.case + str(graph["case"]["id"])
                rdfgraph.add((case_node, rdf.type, orion.Case))
                rdfgraph.add((case_node, orion.id, rdflib.Literal(graph["case"]["id"])))
                for (p, v) in graph["case"]["properties"].items():
                    rdfgraph.add((case_node, orion[p], rdflib.Literal(v)))
                
                # Add the stakeholders and their relationships, which is represented by a blank "stakeholder_in" node.
                for s in graph["stakeholders"]:
                    user_node = ns.user + str(s["id"])
                    rdfgraph.add((user_node, rdf.type, orion.User))
                    rdfgraph.add((user_node, orion.id, rdflib.Literal(s["id"])))
                    rdfgraph.add((user_node, orion.user_id, rdflib.Literal(s["properties"]["user_id"])))

                    rel_node = rdflib.BNode()
                    rdfgraph.add((rel_node, rdf.type, orion.Stakeholder))
                    rdfgraph.add((rel_node, rdf.type, orion.is_stakeholder))
                    rdfgraph.add((rel_node, orion.role, rdflib.Literal(s["role"])))
                    rdfgraph.add((rel_node, orion.case, case_node))
                    rdfgraph.add((rel_node, orion.user, user_node))
                    
                # Add the alternatives and their relationships
                for a in graph["alternatives"]:
                    alt_node = ns.alternative + str(a["id"])
                    rdfgraph.add((alt_node, rdf.type, orion.alternative))
                    rdfgraph.add((alt_node, orion.id, rdflib.Literal(a["id"])))
                    for (p, v) in a["properties"].items():
                        rdfgraph.add((alt_node, orion[p], rdflib.Literal(v)))
                    rdfgraph.add((case_node, orion.alternative, alt_node))
                """
                print(rdfgraph.serialize(format = format).decode("utf-8"))
                return Response(json.dumps(rdfgraph.serialize(format = format).decode("utf-8")))
        else:
            return Response("Invalid user token")    