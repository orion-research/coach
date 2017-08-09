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
import heapq
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

def log(*args, verbose = True):
    message = "" if verbose else "::"
    if verbose:
        message = datetime.now().strftime("%H:%M:%S") + " : "
        message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg).replace("\n", "\n::") + " "
    print(message)
    sys.stdout.flush()
    
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
    
    
    def _get_estimation_method_property_ontology_id_name(self, class_attribute, is_class_property, is_attribute_name = True):
        """
        DESCRIPTION:
            Returns the name or the ontology id of the estimation method or the property defined by class_attribute.
        INPUT:
            class_attribute: The name or the ontology id of an estimation method or a property.
            is_class_property: A boolean, which is True if we are looking for a property attribute, and False if 
                we are looking for an estimation method attribute.
            is_attribute_name: A boolean, which should be True if class_attribute is the name of the
                class and False if class_attribute is the ontology id of the class.
        OUTPUT:
            If is_attribute_name is True, returns the ontology id of the class defined by the name
            class_attribute. Otherwise, returns the name of the class defined by the 
            ontology id class_attribute.
        ERROR:
            Raise a RuntimeError if no match were found with class_attribute.
        """
        if is_attribute_name:
            index_returned = 0
            index_look_for = 2
        else:
            index_returned = 2
            index_look_for = 0
        
        orion_ns = rdflib.Namespace(self.orion_ns)

        if is_class_property:
            orion_class = orion_ns.Property
        else:
            orion_class = orion_ns.EstimationMethod
            
        class_list = self._get_ontology_instances(orion_class)
        for class_tuple in class_list:
            if class_tuple[index_look_for] == class_attribute:
                return class_tuple[index_returned]
        raise RuntimeError("The provided attribute " + class_attribute + " should be in the ontology")
    
    @classmethod
    def _find_dictionary_in_list(cls, dictionary_list, key_name, value):
        for dictionary in dictionary_list:
            if dictionary[key_name] == value:
                return dictionary
        raise KeyError("Dictionary with the property " + key_name + " equals to " + value + " not found.")
    
            
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
        result = [[e[0].properties["uri"], e[0].properties["title"]] for e in query_result]
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
    def get_similar_cases(self, case_db, case_uri, number_of_returned_case, number_ratio_threshold, goal_weight, context_weight,
                          stakeholders_weight):
        # Get all necessary data from the ontology
        case_db_proxy = self.create_proxy(case_db)
           
        goal_class_in_ontology = ["CustomerValue", "FinancialValue", "InternalBusinessValue", "InnovationAndLearningValue", "MarketValue"]
        goal_uri_from_ontology_list = self._get_ontology_instances(None, case_db_proxy, goal_class_in_ontology, [0])
             
        stakeholder_classes_in_ontology = ["RoleType", "RoleFunction", "RoleLevel", "RoleTitle"]
        stakeholder_uri_from_ontology_list = self._get_ontology_instances(None, case_db_proxy, stakeholder_classes_in_ontology, [0])
 
        context_categories_in_ontology = ["OrganizationProperty", "ProductProperty", "StakeholderProperty", 
                                          "DevelopmentMethodAndTechnologyProperty", "MarketAndBusinessProperty"]
        context_categories_in_database = ["organization", "product", "stakeholder", "method", "business"]
        context_from_ontology = {}
        for (database_name, ontology_name) in zip(context_categories_in_database, context_categories_in_ontology):
            context_from_ontology[database_name] = self._get_ontology_instances(ontology_name, case_db_proxy, None, (1, 4, 5))
             
        # Compute vectors
        case_vectors = self._get_case_vectors(case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, 
                                              context_from_ontology, context_categories_in_database)
        
        # result_heap either contains less than number_of_returned_case element, or contains the top number_of_returned_case cases
        # according to their similarity
        result_heap = []
        cases_uri_list = [case_node[0].properties["uri"] for case_node in self.query("MATCH (case:Case) RETURN case")]
         
        for current_case_uri in cases_uri_list:
            if current_case_uri == case_uri:
                continue
             
            current_case_vectors = self._get_case_vectors(current_case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, 
                                                          context_from_ontology, context_categories_in_database)
             
            similarity = self._compute_similarity(case_vectors, current_case_vectors, number_ratio_threshold, goal_weight, context_weight, 
                                                  stakeholders_weight)
            if similarity == 0:
                continue
            
            current_case_node = list(self.query("MATCH (c:Case {uri: $uri}) RETURN c", {"uri": current_case_uri}))[0][0]
            current_case_title = current_case_node.properties["title"]
            alternatives_name_list = self._get_alternative(current_case_uri)
            
            query_selected_alternative = """MATCH (:Case {uri :$uri}) -[:selected_alternative]-> (alt:Alternative)
                                            RETURN alt.title"""
            try:
                selected_alternative = list(self.query(query_selected_alternative, {"uri": current_case_uri}))[0][0]
            except IndexError:
                selected_alternative = None               

            if len(result_heap) == number_of_returned_case:
                heapq.heappushpop(result_heap, (similarity, current_case_title, selected_alternative, alternatives_name_list, 
                                   self._get_properties_estimation_methods(current_case_uri, alternatives_name_list)))
            else:
                heapq.heappush(result_heap, (similarity, current_case_title, selected_alternative, alternatives_name_list,
                   self._get_properties_estimation_methods(current_case_uri, alternatives_name_list)))
                
        result_heap.sort()
        result_heap.reverse()
        return result_heap
        
    
    def _get_case_vectors(self, case_uri, goal_uri_from_ontology_list, stakeholder_uri_from_ontology_list, context_from_ontology, 
                         context_categories_name):
        result = {}
        
        goal_components = self._get_goal_components(case_uri, goal_uri_from_ontology_list)
        result["goal"] = {"vector": goal_components, "number_indexes": set(), "single_select_indexes": set()}

        stakeholders_components = self._get_stakeholder_components(case_uri, stakeholder_uri_from_ontology_list)
        result["stakeholders"] = {"vector": stakeholders_components, "number_indexes": set(), "single_select_indexes": set()}
        
        (context_components, number_indexes, single_select_indexes) = self._get_context_components(case_uri, context_from_ontology, 
                                                                                                   context_categories_name)
        result["context"] = {"vector": context_components, "number_indexes": number_indexes, "single_select_indexes": single_select_indexes}

        return result
    
    
    def _get_goal_components(self, case_uri, goal_uri_from_ontology_list):
        query = """ MATCH (:Case {uri: $case_uri}) -[:goal]-> () --> (goal)
                    RETURN goal.uri
        """
        query_result = self.query(query, {"case_uri": case_uri})
        
        goals_in_case = [e[0] for e in query_result]
        return [1 if goal in goals_in_case else 0 for goal in goal_uri_from_ontology_list]
    
    
    def _get_stakeholder_components(self, case_uri, stakeholder_uri_from_ontology_list):
        query = """ MATCH (:Case {uri :$case_uri}) -[:role]-> (:Role) --> (stakeholder)
                    RETURN stakeholder.uri
        """
        query_result = self.query(query, {"case_uri": case_uri})

        stakeholder_in_case = [e[0] for e in query_result]
        return [1 if stakeholder in stakeholder_in_case else 0 for stakeholder in stakeholder_uri_from_ontology_list]
    
    
    def _get_context_components(self, case_uri, context_from_ontology, categories_name):
        # Cypher does not allow parameter for a relation's label, so string format is used instead.
        query = """ MATCH (:Case {{uri: $case_uri}}) -[:context]-> () -[:{0}]-> () -[grade_id]-> (value)
                    RETURN grade_id, value.value
        """
        
        result = []
        number_indexes = set()
        single_select_indexes = set()
        
        for category_name in categories_name:
            query_result = self.query(query.format(category_name), {"case_uri": case_uri})
            
            context_in_case = defaultdict(list)
            for record in query_result:
                context_in_case[record[0].type].append(record[1])
            
            for context_entry in context_from_ontology[category_name]:
                # context_entry is a list [grade_id, type, possible_values]. possible_values can be either None or a list of string
                current_grade_id = context_entry[0]
                current_type = context_entry[1]
                current_possible_values_list = context_entry[2]
                
                
                if current_type == "text":
                    # At the moment, text entry are not used to compute similarity.
                    pass
                
                elif current_type in ["integer", "float"]:
                    number_indexes.add(len(result))
                    if current_grade_id in context_in_case:
                        field_value = float(context_in_case[current_grade_id][0])
                        result.append(field_value)
                    else:
                        result.append(0)
                
                elif current_type == "single_select":
                    single_select_indexes.add(len(result))
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
                
            
        return (result, number_indexes, single_select_indexes)
    
    
    def _compute_similarity(self, vectors_dict_1, vectors_dict_2, number_ratio_threshold, goal_weight, context_weight, stakeholders_weight):
        goal_vector_1 = vectors_dict_1["goal"]["vector"]
        goal_vector_2 = vectors_dict_2["goal"]["vector"]
        number_indexes = vectors_dict_1["goal"]["number_indexes"]
        single_select_indexes = vectors_dict_1["goal"]["single_select_indexes"]
        goal_information = self._do_compute_similarity(goal_vector_1, goal_vector_2, number_ratio_threshold, number_indexes, 
                                                       single_select_indexes)
        goal_similarity = goal_information[0]
        goal_weight *= goal_information[1]
        
        context_vector_1 = vectors_dict_1["context"]["vector"]
        context_vector_2 = vectors_dict_2["context"]["vector"]
        number_indexes = vectors_dict_1["context"]["number_indexes"]
        single_select_indexes = vectors_dict_1["context"]["single_select_indexes"]
        context_information = self._do_compute_similarity(context_vector_1, context_vector_2, number_ratio_threshold, number_indexes, 
                                                          single_select_indexes)
        context_similarity = context_information[0]
        context_weight *= context_information[1]
        
        stakeholders_vector_1 = vectors_dict_1["stakeholders"]["vector"]
        stakeholders_vector_2 = vectors_dict_2["stakeholders"]["vector"]
        number_indexes = vectors_dict_1["stakeholders"]["number_indexes"]
        single_select_indexes = vectors_dict_1["stakeholders"]["single_select_indexes"]
        stakeholders_information = self._do_compute_similarity(stakeholders_vector_1, stakeholders_vector_2, number_ratio_threshold,
                                                                number_indexes, single_select_indexes)
        stakeholders_similarity = stakeholders_information[0]
        stakeholders_weight *= stakeholders_information[1]
        
        log("goal_similarity :", goal_similarity, type(goal_similarity))
        log("context_similarity :", context_similarity, type(context_similarity))
        log("stakeholders_similarity :", stakeholders_similarity, type(stakeholders_similarity))
        log("goal_weight :", goal_weight, type(goal_weight))
        log("context_weight :", context_weight, type(context_weight))
        log("stakeholders_weight :", stakeholders_weight, type(stakeholders_weight))
        try:
            return ((goal_similarity * goal_weight + context_similarity * context_weight + stakeholders_similarity * stakeholders_weight) /
                    (goal_weight + context_weight + stakeholders_weight))
        except ZeroDivisionError:
            return 0
    
    
    def _do_compute_similarity(self, case_vector_1, case_vector_2, number_ratio_threshold, number_indexes, single_select_indexes):
        
        vector_length = len(case_vector_1)
        log("vector_length :", vector_length)
        if vector_length != len(case_vector_2):
            raise RuntimeError("Both vectors must have the same length, but length are {0} and {1}."
                               .format(vector_length, len(case_vector_2)))
        
        # Jaccard index is used to compute similarity
        number_of_components_both_1 = 0 # Component are identical
        number_of_components_both_0 = 0 # No information provided
        # Components are different is computed by vector_lentgth - identical - no_information
        
        for i in range(vector_length):
            value1 = abs(case_vector_1[i])
            value2 = abs(case_vector_2[i])
            value_min = min(value1, value2)
            value_max = max(value1, value2)
            
            if i in single_select_indexes:
                if value_max == 0:
                    number_of_components_both_0 += 1
                elif value_min == value_max:
                    number_of_components_both_1 += 1
                    
            elif i in number_indexes:
                if value_max == 0:
                    number_of_components_both_0 += 1
                elif value_min != 0 and value_max / value_min < number_ratio_threshold:
                    number_of_components_both_1 += 1
            
            else:
                if value_max > 1:
                    raise RuntimeError("When the component is neither a number nor a single select, value in the cases' vector must be " +
                                       "0 or 1, but it is {0} for index {1}.".format(value_max, i))
                if value_max == 0:
                    number_of_components_both_0 += 1
                elif value_min == 1:
                    number_of_components_both_1 += 1
             
        try:
            number_of_meaningful_components = vector_length - number_of_components_both_0
            return (number_of_components_both_1 / number_of_meaningful_components, number_of_meaningful_components)
        except ZeroDivisionError:
            return (0, 0)
        
    def _get_alternative(self, case_uri):
        query = """ MATCH (:Case {uri: $uri}) -[:alternative]-> (alternative:Alternative)
                    RETURN alternative.title
                """
        
        result = [alt[0] for alt in self.query(query, {"uri": case_uri})]
        return result
    
    @endpoint("/_get_properties_estimation_methods", ["GET"], "application/json")
    def _get_properties_estimation_methods(self, case_uri, alternatives_name_list):
        query = """ MATCH (case:Case {uri: $uri}) -[:property]-> (property:Property) -[:ontology_id]-> (prop_ontology_id)
                    MATCH (property) <-[:belong_to_property]- (estimation:Estimation) -[:ontology_id]-> (estimation_ontology_id)
                    MATCH (estimation) -[:belong_to_alternative]-> (alternative:Alternative)
                    RETURN DISTINCT prop_ontology_id.uri, estimation_ontology_id.uri, estimation, alternative.title
                """
        query_result = self.query(query, {"uri": case_uri})

        result = []
        for record in query_result:
            property_name = self._get_estimation_method_property_ontology_id_name(record[0], True, False)
            try:
                property_dictionary = self._find_dictionary_in_list(result, "property_name", property_name) 
            except KeyError:
                property_dictionary = {"property_name": property_name, "estimation_methods": []}
                result.append(property_dictionary)
            
            em_name = self._get_estimation_method_property_ontology_id_name(record[1], False, False)
            try:
                em_dictionary = self._find_dictionary_in_list(property_dictionary["estimation_methods"], "estimation_method_name", em_name)
            except KeyError:
                estimated_values = [{"up_to_date": True, "value": "---", "alternative_name": alt} for alt in alternatives_name_list]
                em_dictionary = {"estimation_method_name": em_name, "estimated_values": estimated_values}
                property_dictionary["estimation_methods"].append(em_dictionary)
            
            alternative_name = record[3]
            estimated_value = self._find_dictionary_in_list(em_dictionary["estimated_values"], "alternative_name", alternative_name)

            estimation = record[2]
            estimated_value["up_to_date"] = estimation.properties["up_to_date"]
            estimated_value["value"] = estimation.properties["value"]
            
        return result

if __name__ == "__main__":
    KnowledgeRepositoryService(sys.argv[1]).run()




























