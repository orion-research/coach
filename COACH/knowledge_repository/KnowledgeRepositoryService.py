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
        
class KnowledgeRepositoryService(Microservice):

    """
    Implements the KR as a microservice with a web service interface.
    """

    def __init__(self, settings_file_name = None, working_directory = None):
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file_:
            fileData = file_.read()
        secret_data = json.loads(fileData)

        # Initialize the graph database
        self._db = GraphDatabase.driver("bolt://localhost", auth=basic_auth(secret_data["neo4j_user_name"], secret_data["neo4j_password"]))
        self.orion_ns = "http://www.orion-research.se/ontology#"
        
        # Initialize proxies
        self.authentication_proxy = self.create_proxy(self.get_setting("authentication_service"))
            
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
    
    def delete_case(self, case_uri, session=None):
        delete_case_relations_query =   """ Match (:Case {uri: $uri}) -[r*]-> ()
                                            UNWIND r AS rs
                                            DETACH DELETE rs
                                        """
        delete_detached_node_query = """Match (n)
                                        Where not (n) -- ()
                                        Delete n
                                    """

        close_session = False
        if session is None:
            close_session = True
            session = self.open_session()
        self.query(delete_case_relations_query, {"uri": case_uri}, session)
        self.query(delete_detached_node_query, session=session)
        if close_session:
            self.close_session(session)
        
    
    @endpoint("/export_case", ["GET"], "application/json")    
    def export_case(self, graph_description, format_):
        """
        Endpoint for handling the storage of a complete case to the KR.
        """
        case_graph = rdflib.Graph()
        case_graph.parse(data=graph_description, format=format_)
        
        check_unique_literal_query = """SELECT ?s ?p (count(?o) as ?count)
                                        WHERE {
                                            ?s ?p ?o .
                                            FILTER(isLiteral(?o))
                                        }
                                        GROUP BY ?s ?p
                                        HAVING (count(?o) > 1)
                                    """
        query_result = list(case_graph.query(check_unique_literal_query))
        if len(query_result) != 0:
            subjet_uri = str(query_result[0][0].toPython())
            predicate = str(query_result[0][1].toPython())
            literal_count = str(query_result[0][2].toPython())
            other_uri_predicate_pair_count = str(len(query_result) - 1)
            raise RuntimeError("The graph must not contain an uri linked to several literals with the same predicate, but the uri " +
                               subjet_uri + " is linked to " + literal_count + " literals by the predicate " + predicate +
                               ". There is " + other_uri_predicate_pair_count + " other uri-predicate pair in the same case in the graph.")
        
        with self.open_session() as session:
            # The case is deleted from the knowledge repository to handle suppressed nodes from the database
            orion_ns = rdflib.Namespace(self.orion_ns)
            case_uri = case_graph.query("SELECT ?case_uri WHERE {?case_uri a orion:Case.}", initNs={"orion": orion_ns})
            case_uri = list(case_uri)[0][0].toPython()
            self.delete_case(case_uri, session)
            
            for s, p, o in case_graph:
                if isinstance(s, rdflib.term.Literal):
                    raise RuntimeError("A subject must not be a Literal")
                
                predicate_name = split_uri(p)[1]
#                     if not predicate_name.islower():
#                         raise RuntimeError("The predicate " + predicate_name + " contains upper cases letters.")
                
                if predicate_name == "type":
                    if not str(o).startswith(self.orion_ns):
                        raise RuntimeError("The type of a node must be in the ontology namespace")
                    label = str(o)[len(self.orion_ns):]
                    # Can not use a parameter for label, as it is not supported in neo4j
                    # TODO: Malicious code injection might be possible
                    query = "MERGE (node {uri: $uri}) SET node :`" + label + "`"
                    self.query(query, {"uri": str(s)}, session)
                    continue
                    
                if isinstance(o, rdflib.Literal):
                    # Can not use the name of the property as a parameter, as it is not supported in neo4j
                    # TODO: Malicious code injection might be possible
                    query = "MERGE (node {uri: $uri}) SET node.`" + predicate_name + "` = $value"
                    self.query(query, {"uri": str(s), "value":o.toPython()}, session)
                    continue
                
                # TODO: Malicious code injection might be possible
                query = """ MERGE (subject_node {uri: $subject_uri}) 
                            MERGE (object_node {uri: $object_uri})
                            MERGE (subject_node) -[:`""" + predicate_name + """`]-> (object_node)
                        """
                self.query(query, {"subject_uri": str(s), "object_uri": str(o)}, session)
                
        
    @endpoint("/get_cases", ["GET"], "application/json")
    def get_cases(self, user_id):
        query = """ Match ({uri: $user_uri}) <-[:person]- (:Role) <-[:role]- (case:Case)
                    Return case
                """
        user_uri = self.authentication_proxy.get_user_uri(user_id=user_id)
        query_result = self.query(query, {"user_uri": user_uri})
        result = [[e.values()[0].properties["uri"], e.values()[0].properties["title"]] for e in query_result]
        return result
    
    @endpoint("/import_case", ["GET"], "application/json")
    def import_case(self, case_uri, format_):
        query = """ MATCH (case:Case {uri:$case_uri}) -[r*]-> (n)
                    RETURN n, case, r
                """
        query_result = self.query(query, {"case_uri": case_uri})
        case_graph = self.get_graph_from_query_result(list(query_result))
        orion_ns = rdflib.Namespace(self.orion_ns)
        case_uri = case_graph.query("SELECT ?case_uri WHERE {?case_uri a orion:Case.}", initNs={"orion": orion_ns})
        case_uri = list(case_uri)[0][0].toPython()
        case_graph_description = case_graph.serialize(format=format_).decode("utf8")
        return {"case_graph_description": case_graph_description, "case_uri": case_uri}
            
    def get_graph_from_query_result(self, query_result_list):
        graph_description = ""
        id_to_uri = {}
        
        # Get the description of the case
        graph_description += self.get_node_description(query_result_list[0][1], id_to_uri)
        for entry in query_result_list:
            graph_description += self.get_node_description(entry[0], id_to_uri)
        
        for entry in query_result_list:
            relations_list = entry[2]
            for relation in relations_list:
                subject_uri = id_to_uri[relation.start]
                object_uri = id_to_uri[relation.end]
                predicate = self.orion_ns + relation.type
                graph_description += "<" + subject_uri + "> <" + predicate + "> <" + object_uri + "> .\n"
        
        case_graph = rdflib.Graph()
        case_graph.parse(data=graph_description, format="n3")
        return case_graph
    
    def get_node_description(self, node, id_to_uri_dict):
        node_uri = node.properties["uri"]
        del node.properties["uri"]
        if node.id in id_to_uri_dict:
            return ""       
        id_to_uri_dict[node.id] = node_uri
        
        result = ""
        for key in node.properties:
            subject = node_uri
            predicate = self.orion_ns + key
            object_ = str(node.properties[key]).replace("\n", "\\u000A").replace("\r", "\\u000D").replace('"', "\\u0022")
            result += "<" + subject + "> <" + predicate + '> "' + object_ + '" .\n'
        
        try:
            node_type = self.orion_ns + node.labels.pop()
            result += "<" + node_uri + "> " + "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <" + node_type + "> .\n"
        except KeyError:
            pass
        return result
        
        
    
    
    
    
    
    
    
    