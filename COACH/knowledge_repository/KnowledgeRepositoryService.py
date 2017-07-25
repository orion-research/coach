"""
Created on 13 juni 2016

@author: Jakob Axelsson

Knowledge repository for storing data about finished decision cases to use for guidance in new decision cases.
"""

# Standard libraries
import json
import os
import sys
from collections import defaultdict
from scipy import spatial
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

# TODO: to suppress
from datetime import datetime
import inspect
        
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
        
        self.ontology = None
        

    def _get_ontology(self, case_db_proxy = None):
        """
        DESCRIPTION:
            Return the ontology stored in the database. The query to the database is done only once and the result is stored. 
            Thanks to that, the following times, the stored object can be returned immediately.
        INPUT:
            case_db_proxy: The proxy to access database. It can be omitted if the ontology has already been got from the database.
        OUTPUT:
            The ontology stored in the database. 
        ERROR:
            Throw a TypeError if case_db_proxy is omitted whereas the ontology has not yet been got from the database.
        """
        if not self.ontology:
            self.ontology = rdflib.ConjunctiveGraph()
            self.ontology.parse(data = case_db_proxy.get_ontology(format_ = "ttl"), format = "ttl")
        return self.ontology
    
    
    def _get_ontology_instances(self, class_name = None, case_db_proxy = None, class_name_list = None, returned_information= (0, 1, 2, 3)):
        """
        DESCRIPTION:
            Return a list containing all the instances of the given class in the ontology.
        INPUT:
            class_name: The name of a single class in the ontology. Requested information about all elements of this class present in
                the ontology will be returned. Exactly one of class_name and class_name_list must be provided.
            case_db_proxy: The proxy to access database. It can be omitted if the ontology has already been got from the database.
            class_name_list: A list of class' name in the ontology. Requested information about all elements of these classes present in
                the ontology will be returned. Exactly one of class_name and class_name_list must be provided.
            returned_information: An iterable containing the indexes of the requested informations: information available are:
                instances' uri, gradeId, title, description, type and possibleValues. Each of these information will be returned if
                returned_information contains their index (from 0 for instances' uri to 5 for possibleValues). Type and possibleValues
                are optional, None will be set if they are not defined for the current instance. If there is only one element (e.g. (2,)), 
                a simple list will be returned (e.g. ["Increase sales", "Sustain/retain market position"...] instead of 
                [["Increase sales"], ["Sustain/retain market position"]...]). 
                The elements in the inner list are in the same order than the indexes in returned_information.
        OUTPUT:
            Return a list containing all the instances of the given class in the ontology. Each element of this list provides the requested
            information by returned_information.
            Elements are sorted first according to their class name, then their grade id. That means that if class_name_list contains two
            elements, all instances of the first class name will be before any instances of the second class name.
        ERROR:
            A RuntimeError is raised if both class_name and class_name_list are provided, or both are not.
            An IndexError is raised if returned_information contains an integer greater than 5 or smaller than 0.
            A TypeError is raised if returned_information contains a non-integer.
        """
        if (class_name is None and class_name_list is None) or (class_name is not None and class_name_list is not None):
            raise RuntimeError("Exactly one argument among class_name and class_name_list must be provided")
        
        if class_name is not None:
            class_name_list = [class_name]
        
        orion_ns = rdflib.Namespace(self.orion_ns)
        q = """\
        SELECT ?inst ?grade_id ?title ?description ?type ?possible_values_start_list
        WHERE {
            ?inst a ?class_name .
            ?inst orion:gradeId ?grade_id .
            OPTIONAL { ?inst orion:title ?title . }
            OPTIONAL { ?inst orion:description ?description . }
            OPTIONAL { ?inst orion:type ?type . }
            OPTIONAL { ?inst orion:possibleValues ?possible_values_start_list . }
        }
        ORDER BY ?grade_id
        """
        
        result = []
        for class_name in class_name_list:
            if not isinstance(class_name, rdflib.term.URIRef):
                class_name = orion_ns[class_name]
            
            query_result = self._get_ontology(case_db_proxy).query(q, initNs = {"orion": orion_ns}, 
                                                                   initBindings = {"?class_name": rdflib.URIRef(class_name)})
            class_result = []
            for line in query_result:
                if len(returned_information) == 1:
                    class_result.append(self._get_instances_element(line, returned_information[0]))
                else:
                    class_result.append([self._get_instances_element(line, index) for index in returned_information])
            
            result += class_result
            
        return result
    
    
    def _get_instances_element(self, line, index):
        if line[index] is None:
            return None
        
        if index == 5:
            # The fifth index represent possible_values. The current value line[index] is the beginning of an rdf collection. 
            possible_values_list = rdflib.collection.Collection(self._get_ontology(), line[index])
            return [e.toPython() for e in possible_values_list]
        return line[index].toPython()
    
            
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
            with self.open_session() as s:
                result = s.run(query, context)
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
        
        check_blank_node_absence_query = """SELECT ?s ?p ?o
                                            WHERE {
                                                ?s ?p ?o .
                                                FILTER(isBlank(?s) || isBlank(?o))
                                            }
                                        """
        query_result = list(case_graph.query(check_blank_node_absence_query))
        if len(query_result) != 0:
            raise RuntimeError("Blank node are not handled when exporting data to the knowledge repository, but {0} were found."
                               .format(len(query_result)))
        
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
            case_uri = case_graph.query("SELECT ?case_uri WHERE {?case_uri a orion:Case.}", initNs={"orion": rdflib.Namespace(self.orion_ns)})
            if len(case_uri) != 1:
                raise RuntimeError("There must be exactly one case in the provided graph, but {0} were found.".format(len(case_uri)))
            case_uri = list(case_uri)[0][0].toPython()
            self.delete_case(case_uri, session)
            
            for s, p, o in case_graph:
                if isinstance(s, rdflib.term.Literal):
                    raise RuntimeError("A subject must not be a Literal")
                
                predicate_name = split_uri(p)[1]
                if predicate_name == "uri":
                    raise RuntimeError("Can not handle triplet whose predicate name is 'uri', as it is already used for the identifier " +
                                       "property in neo4j. Triplet is :({0}, {1}, {2}).".format(s, p, o))
                    
                if predicate_name == "type":
                    if not str(o).startswith(self.orion_ns):
                        raise RuntimeError("The type of a node must be in the ontology namespace")
                    label = str(o)[len(self.orion_ns):]
                    # Can not use a parameter for label, as it is not supported in neo4j
                    # TODO: Malicious code injection might be possible
                    query = "MERGE (node {uri: $uri}) SET node :`" + label + "`"
                    self.query(query, {"uri": str(s)}, session)
                    continue
                    
                if isinstance(o, rdflib.term.Literal):
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
        result = [[e[0].properties["uri"], e.values()[0].properties["title"]] for e in query_result]
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
                graph_description += "<{0}> <{1}> <{2}> .\n".format(subject_uri, predicate, object_uri)
        
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
            result += '<{0}> <{1}> "{2}" .\n'.format(subject, predicate, object_)
        
        try:
            node_type = self.orion_ns + node.labels.pop()
            result += "<" + node_uri + "> " + "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <" + node_type + "> .\n"
        except KeyError:
            pass
        return result
    
    
    @endpoint("/get_similar_cases", ["GET"], "application/json")
    def get_similar_cases(self, case_db, case_uri, similarity_treshold):
        # Get all necessary data from the ontology
        case_db_proxy = self.create_proxy(case_db)
          
        goal_class_in_ontology = ["CustomerValue", "FinancialValue", "InternalBusinessValue", "InnovationAndLearningValue", "MarketValue"]
        goal_uri_from_ontology_list = self._get_ontology_instances(None, case_db_proxy, goal_class_in_ontology, [0])
            
        stakeholder_classes_in_ontology = ["RoleType", "RoleFunction", "RoleLevel", "RoleTitle"]
        stakeholder_uri_from_ontology_list = self._get_ontology_instances(None, case_db_proxy, stakeholder_classes_in_ontology, [0])

        context_categories_in_ontology = ["OrganizationProperty", 
                                          "ProductProperty", 
                                          "StakeholderProperty", 
                                          "DevelopmentMethodAndTechnologyProperty", 
                                          "MarketAndBusinessProperty"]
        context_categories_in_database = ["organization", "product", "stakeholder", "method", "business"]
        
        context_from_ontology = {}
        for (database_name, ontology_name) in zip(context_categories_in_database, context_categories_in_ontology):
            context_from_ontology[database_name] = self._get_ontology_instances(ontology_name, case_db_proxy, None, (1, 4, 5))
            
        # Compute vectors
        case_vector = self._get_case_vector(case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, context_from_ontology, 
                                            context_categories_in_database)
        
        result = []
        cases_uri_list = [case_node[0].properties["uri"] for case_node in self.query("MATCH (case:Case) RETURN case")]
        for current_case_uri in cases_uri_list:
            current_case_vector = self._get_case_vector(current_case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, 
                                                        context_from_ontology, context_categories_in_database)
            
            # If one of those vectors has only 0 terms, numpy.nan will be returned, but numpy.nan > 0 is False.
            # Consequently, if a case has only 0 terms, it is similar to not a single case (even itself).
            similarity = float(1 - spatial.distance.cosine(case_vector, current_case_vector))
            if similarity > similarity_treshold:
                result.append((current_case_uri, similarity))
        return result
        
    
    def _get_case_vector(self, case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, context_from_ontology, 
                         context_categories_name):
        result = self._get_goal_dimensions(case_uri, goal_uri_from_ontology_list)
        result += self._get_stakeholder_dimensions(case_uri, stakeholder_uri_from_ontology_list)
        result += self._get_context_dimensions(case_uri, context_from_ontology, context_categories_name)
        return result
    
    
    def _get_goal_dimensions(self, case_uri, goal_uri_from_ontology_list):
        query = """ MATCH (:Case {uri: $case_uri}) -[:goal]-> () --> (goal)
                    RETURN goal
        """
        query_result = self.query(query, {"case_uri": case_uri})
        
        goals_in_case = [e[0].properties["uri"] for e in query_result]
        return [1 if goal in goals_in_case else 0 for goal in goal_uri_from_ontology_list]
    
    
    def _get_stakeholder_dimensions(self, case_uri, stakeholder_uri_from_ontology_list):
        query = """ MATCH (:Case {uri :$case_uri}) -[:role]-> (:Role) --> (stakeholder)
                    RETURN stakeholder
        """
        query_result = self.query(query, {"case_uri": case_uri})

        count_stakeholder_in_case = defaultdict(int)
        for record in query_result:
            record_uri = record[0].properties["uri"]
            count_stakeholder_in_case[record_uri] += 1

        return [count_stakeholder_in_case[stakeholder] for stakeholder in stakeholder_uri_from_ontology_list]
    
    
    def _get_context_dimensions(self, case_uri, context_from_ontology, categories_name):
        query = """ MATCH (:Case {{uri: $case_uri}}) -[:context]-> () -[:{0}]-> () -[grade_id]-> (value)
                    RETURN grade_id, value
        """
        
        result = []
        for category_name in categories_name:
            query_result = self.query(query.format(category_name), {"case_uri": case_uri})
            
            context_in_case = defaultdict(list)
            for record in query_result:
                context_in_case[record[0].type].append(record[1].properties["value"])
            
            for context_entry in context_from_ontology[category_name]:
                # context_entry is a list [grade_id, type, possible_values]. possible_values can be either None or a list of string
                current_grade_id = context_entry[0]
                current_type = context_entry[1]
                current_possible_values_list = context_entry[2]
                
                if current_type == "text":
                    # At the moment, text entry are not used to compute similarity.
                    pass
                
                elif current_type in ["integer", "float"]:
                    if current_grade_id in context_in_case:
                        field_value = float(context_in_case[current_grade_id][0])
                        result.append(field_value)
                    else:
                        result.append(0)
                
                elif current_type == "single_select":
                    if current_grade_id in context_in_case:
                        # 0 is the value when the user selects unknown. Consequently, the first value in the ontology is 1, 
                        # hence 'index + 1'
                        selected_value = context_in_case[current_grade_id][0]
                        result.append(current_possible_values_list.index(selected_value) + 1)
                    else:
                        result.append(0)
                
                elif current_type == "multi_select":
                    if current_grade_id not in context_in_case:
                        result += [0] * len(current_possible_values_list)
                    else:
                        for possible_value in current_possible_values_list:
                            selected_values_list = context_in_case[current_grade_id]
                            result.append(1 if possible_value in selected_values_list else 0)
                else:
                    raise RuntimeError("Unknown type {0}. Allowed types are 'text', 'integer', 'float', 'single_select' and 'multi_select'."
                                       .format(current_type))
                    
            
        return result
    
    
    def _compute_similarity(self, case_vector1, case_vector2):
        if len(case_vector1) != len(case_vector2):
            raise RuntimeError("Both vectors must have the same length, but length are {0} and {1}."
                               .format(len(case_vector1), len(case_vector2)))
            
        






























