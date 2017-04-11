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

    def __init__(self, settings_file_name = None, working_directory = None):
        """
        The case database is initialized by loading the ontology from file.
        """
        
        super().__init__(settings_file_name, working_directory = working_directory)
        # Load the ontology from file
        self.orion_ns = "http://www.orion-research.se/ontology#"  # The name space for the ontology used
        self.data_ns = self.host + "/data#"  # The name space for this data source

        # Namespace objects cannot be stored as object attributes, since they collide with the microservice mechanisms
        orion_ns = rdflib.Namespace(self.orion_ns)
        data_ns = rdflib.Namespace(self.data_ns)

        self.ontology = rdflib.ConjunctiveGraph()
        self.ontology.bind("data", data_ns)
        self.ontology.bind("orion", orion_ns)
        ontology_path = os.path.join(self.working_directory, os.pardir, "Ontology.ttl")
        self.ontology.parse(source = ontology_path, format = "ttl")
        
        # Populate the database by all instance elements in the ontology, ensuring to not duplicate data already there.
        for s, _, o in self.ontology.triples( (None, rdflib.RDF.type, None) ):
            (_, ns1, _) = self.ontology.compute_qname(s)
            (_, ns2, r2) = self.ontology.compute_qname(o)
            # Only include triples where both subject and object are from the ORION ontology
            if str(ns1) == self.orion_ns and str(ns2) == self.orion_ns:
                
                # If this resource is not in the database, add it
                self.add_resource_with_uri(r2, str(s))

                # Update the properties gradeId, title and description (if they exist), to ensure that the latest ontology data is used.
                gradeId = self.ontology.value(s, orion_ns.gradeId, None)
                if gradeId:
                    q = """MATCH (r:$label { uri : { uri } }) SET r.gradeId = {value}"""
                    params = { "uri" : str(s), "value" : gradeId }
                    self.query(q, params)

                title = self.ontology.value(s, orion_ns.title, None)
                if title:
                    q = """MATCH (r:$label { uri : { uri } }) SET r.title = {value}"""
                    params = { "uri" : str(s), "value" : title }
                    self.query(q, params)

                description = self.ontology.value(s, orion_ns.description, None)
                if description:
                    q = """MATCH (r:$label { uri : { uri } }) SET r.description = {value}"""
                    params = { "uri" : str(s), "value" : description }
                    self.query(q, params)
    
    
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
            
            # Then set the uri attribute of the case node.
            q2 = """MATCH (c:Case:$label) WHERE id(c) = {case_id} SET c.uri = {uri}"""
            params2 = { "case_id": case_id, "uri": self.id_to_uri(case_id) }
            self.query(q2, params2, s)
            
            # Then create the relationship
            q3 = """\
            MATCH (c:Case:$label), (u:User:$label)
            WHERE id(c) = {case_id} AND u.user_id = {initiator}
            CREATE (c) -[:Stakeholder {role: "initiator"}]-> (u)
            """
            params3 = { "case_id": case_id, "initiator": initiator }
            self.query(q3, params3, s)
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
        """
        
        return Response(json.dumps(self.ontology.serialize(format = format).decode("utf-8")))
     
     
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
                # Serialize case data as RDF triples by transforming graph to an rdflib graph, and then serialize it using the formats provided in the rdflib.
                (nodes, edges, properties, labels) = self.get_graph_starting_in_node(int(case_id))

                # Create the name spaces
                rdf = rdflib.RDF
                ns = rdflib.Namespace(self.host + "/data#")  # The name space for this data source
                orion = rdflib.Namespace("https://www.orion-research.se/ontology#")  # The name space for the ontology used
                neo4j = rdflib.Namespace("https://www.orion-research.se/neo4j#") # The name space for annotations related to neo4j <-> triples mapping

                # Create the graph and bind the name spaces    
                rdfgraph = rdflib.ConjunctiveGraph()
                rdfgraph.bind("ns", ns)
                rdfgraph.bind("orion", orion)
                rdfgraph.bind("neo4j", neo4j)
                
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
                    if e in properties[e]:
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
                        # Add neo4j annotations to make it possible to map the triples back into a neo4j graph
                        rdfgraph.add((ns.node + str(e), rdf.type, neo4j.Relationship))
                        rdfgraph.add((ns.node + str(e), neo4j.from_node, ns.node + str(n1)))
                        rdfgraph.add((ns.node + str(e), neo4j.to_node, ns.node + str(n2)))
                    else:
                        # If the edge has no properties, there is no need to create a node for it
                        rdfgraph.add((ns.node + str(n1), orion[labels[e].lower()], ns.node + str(n2)))
                
                print(rdfgraph.serialize(format = format).decode("utf-8"))
                return Response(json.dumps(rdfgraph.serialize(format = format).decode("utf-8")))
        else:
            return Response("Invalid user token")
    
        
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
    
    
    @endpoint("/get_data_namespace", ["GET", "POST"])
    def get_data_namespace(self):
        """
        Returns the namespace used for data in this case database.
        """
        return Response(json.dumps(self.data_ns))
    
    
    @endpoint("/add_resource", ["POST"])
    def add_resource(self, user_id, user_token, resource_class):
        """
        Adds a new resource of the given resource_class, and returns its generated URI.
        """

        # TODO: Add ontology and stakeholder checks.
        
        # A resource is stored in Neo4j as a node with the resource_class as a label.
        # The database id is used as the last part of the returned URI.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            s = self.open_session()
            # First, create the resource and get back its id, which is used to generate the URI.
            q = """CREATE (r:$class:$label) RETURN id(r) AS id"""
            resource_id = self.query(q, { "class" : resource_class }).single()["id"]
            uri = self.id_to_uri(resource_id)
            # Then, set the uri property of the node to the generated URI.
            q = """MATCH (r:$label) WHERE id(r) = {r_id} SET r.uri = {uri}"""
            params = { "r_id" : resource_id, "uri" : uri }
            self.query(q, params)
            self.close_session(s)
            return Response(json.dumps(uri))        
        else:
            return Response("Invalid user token")

    
    def add_resource_with_uri(self, resource_class, uri):
        """
        Adds a new resource of the given resource_class, where the uri is provided.
        If a node with the uri already exists, nothing is done.
        This is used to store relations to other namespaces in the database.
        It is only available internally in the CaseDB to set up elements from the ontology.
        """

        q = """MERGE (r:$class:$label { uri : { uri } } )"""
        self.query(q, { "class" : resource_class, "uri" : uri })

    
    @endpoint("/remove_resource", ["GET", "POST"])
    def remove_resource(self, user_id, user_token, resource):
        """
        Removes a resource, and all properties to and from it.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MATCH (r:$label { uri: {uri} }) DETACH DELETE r"""
            self.query(q, { "uri" : resource })
            return Response("Ok")        
        else:
            return Response("Invalid user token")

    
    @endpoint("/add_datatype_property", ["GET", "POST"])
    def add_datatype_property(self, user_id, user_token, resource, property_name, value):
        """
        Adds value to resource under the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
        # A datatype property is stored in Neo4j as a node attribute.
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MATCH (r:$label { uri : { uri } }) SET r.$property_name = {value}"""
            params = { "uri" : resource, "property_name" : property_name, "value" : value }
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")
        
        
    @endpoint("/add_object_property", ["GET", "POST"])
    def add_object_property(self, user_id, user_token, resource1, property_name, resource2):
        """
        Relates resource1 to resource2 through the given property_name.
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token) and self.is_stakeholder(user_id, case_id):
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """\
            MATCH (r1:$label { uri : { uri1 }}), (r2:$label  { uri : { uri2 }})
            CREATE (r1) -[:$property_name]-> (r2)
            """
            params = { "uri1" : resource1, "uri2" : resource2, "property_name" : property_name }
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")


    @endpoint("/get_datatype_property", ["GET", "POST"])
    def get_datatype_property(self, user_id, token, resource, property_name):
        """
        Returns a value, for which there is a datatype property relation called property_name
        from the provided resource. 
        """

        # TODO: Add ontology and stakeholder checks.
        
#        if self.is_stakeholder(user_id, case_id) and (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token) or 
#                                                      self.authentication_service_proxy.check_delegate_token(user_id = user_id, delegate_token = token, case_id = case_id)):
        if (self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = token)):
            try:
                q = """MATCH (r:$label { uri : { uri } }) RETURN r.$property_name AS value"""
                params = { "uri": resource, "property_name": property_name }
                query_result = self.query(q, params).single()["value"]
                return Response(json.dumps(query_result))
            except:
                return Response(json.dumps(None))
        else:
            return Response("Invalid user or delegate token")
        
        
    @endpoint("/get_object_properties", ["GET", "POST"])
    def get_object_properties(self, user_id, user_token, resource, property_name):
        """
        Returns a list of resources, for which there is a datatype property relation called property_name
        from the provided resource. property_name is not given as a full uri, but just as the name.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """\
            MATCH (r1:$label { uri : { uri1 } }) -[:$property_name]-> (r2:$label)
            RETURN r2.uri AS uri2"""
            params = { "uri1" : resource, "property_name" : property_name }
            result = self.query(q, params)
            if result:
                return Response(json.dumps([res["uri2"] for res in result]))
            else:
                return Response(json.dumps([]))
        else:
            return Response("Invalid user token")


    @endpoint("/remove_datatype_property", ["GET", "POST"])
    def remove_datatype_property(self, user_id, user_token, resource, property_name):
        """
        Remove all properties called property_name from the resource.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MATCH (r:$label { uri : { uri } }) REMOVE r.$property_name"""
            self.query(q, { "uri" : resource, "property_name" : property_name })
            return Response("Ok")        
        else:
            return Response("Invalid user token")


    @endpoint("/remove_object_property", ["GET", "POST"])
    def remove_object_property(self, user_id, user_token, resource1, property_name, resource2):
        """
        Remove the object property relating resource1 to resource 2.
        """

        # TODO: Add ontology and stakeholder checks.
        
        if self.authentication_service_proxy.check_user_token(user_id = user_id, user_token = user_token):
            q = """MATCH (r:$label { uri : {uri1} } ) -[p:$property_name]-> (:$label { uri : {uri2} }) DELETE p"""
            params = { "uri1" : resource1, "property_name" : property_name, "uri2" : resource2 }
            self.query(q, params)
            return Response(json.dumps("Ok"))
        else:
            return Response("Invalid user token")
