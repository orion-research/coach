'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''


# Database connection
from neo4j.v1 import GraphDatabase, basic_auth


class CaseDatabase:
    
    """
    The case database provides the interface to the database for storing case information. 
    It wraps an API around a standard graph DBMS.
    
    TODO: 
    - All actions should generate entries into a history, showing who, when, and what has been done.
    This is useful for being able to analyze decision processes. 
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


    def user_ids(self):
        """
        Queries the case database and returns an iterable of all user ids (the name the user uses to log in).
        """
        q = """MATCH (u:User:{label}) RETURN u.user_id AS user_id"""
        return [result["user_id"] for result in self.query(q, locals())]
    
    
    def user_cases(self, user_id):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        q = """MATCH (case:Case:{label}) -[:Stakeholder]-> (user:{label} {{user_id: "{user_id}"}}) RETURN id(case) AS id, case.title AS title"""
        return [(result["id"], result["title"]) for result in self.query(q, locals())]
        
    
    def create_user(self, user_id):
        """
        Creates a new user in the database, if it is not already there. 
        """
        q = """MERGE (u:User:{label} {{user_id : "{user_id}"}})"""
        self.query(q, locals())
        

    def create_case(self, title, description, initiator):
        """
        Creates a new case in the database, with a relation to the initiating user (referenced by user_id). 
        It returns the database id of the new case.
        """

        s = self.open_session()
        # First create the new case node, and get it's id
        q1 = """CREATE (c:Case:{label} {{title: "{title}", description: "{description}"}}) RETURN id(c) AS case_id"""
        case_id = next(iter(self.query(q1, locals(), s)))["case_id"]
        
        # Then create the relationship
        q2 = """\
        MATCH (c:Case:{label}), (u:User:{label})
        WHERE id(c) = {case_id} AND u.user_id = "{initiator}"
        CREATE (c) -[:Stakeholder {{role: "initiator"}}]-> (u)
        """
        self.query(q2, locals(), s)
        self.close_session(s)
        return case_id        
        
    
    def change_case_description(self, case_id, title, description):
        """
        Changes the title and description fields of the case with case_id.
        """
        q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} SET case.title = "{title}", case.description = "{description}" """
        self.query(q, locals())
           
        
    def get_case_description(self, case_id):
        """
        Returns a tuple containing the case title and description for the case with case_id.
        """
        q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} RETURN case.title AS title, case.description AS description"""
        result = next(iter(self.query(q, locals())))
        return (result["title"], result["description"])
        

    def add_stakeholder(self, user_id, case_id, role = "contributor"):
        """
        Adds a user as a stakeholder with the provided role to the case. 
        If the user is already a stakeholder, nothing is changed. 
        """
        q = """\
        MATCH (c:Case:{label}), (u:User:{label})
        WHERE id(c) = {case_id} AND u.user_id = "{user_id}"
        MERGE (c) -[r:Stakeholder]-> (u)
        ON CREATE SET r.role = "{role}"
        """
        self.query(q, locals())

    
    def create_alternative(self, title, description, case_id):
        """
        Creates a decision alternative and links it to the case.
        """

        s = self.open_session()
        # First create the new alternative, and get it's id
        q1 = """CREATE (a:Alternative:{label} {{title: "{title}", description: "{description}"}}) RETURN id(a) AS alt_id"""
        new_alternative = next(iter(self.query(q1, locals(), s)))["alt_id"]
        
        # Then create the relationship to the case
        q2 = """\
        MATCH (c:Case:{label}), (a:Alternative:{label})
        WHERE id(c) = {case_id} AND id(a) = {new_alternative}
        CREATE (c) -[:Alternative]-> (a)
        """
        self.query(q2, locals(), s)
        self.close_session(s)
        return case_id        

    
    def get_decision_process(self, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        try:
            q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} RETURN case.decision_process AS process LIMIT 1"""
            return next(iter(self.query(q, locals())))["process"]
        except:
            return None
    
    
    def change_decision_process(self, case_id, url):
        """
        Changes the decision process url associated with a case.
        """
        q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} SET case.decision_process = "{url}" """
        self.query(q, locals())

    
    def change_case_property(self, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} SET case.{name} = "{value}\""""
        self.query(q, locals())
        
    
    def get_case_property(self, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        try:
            q = """MATCH (case:Case:{label}) WHERE id(case) = {case_id} RETURN case.{name} AS name"""
            return next(iter(self.query(q, locals())))["name"]
        except:
            return None
        
    
    def get_decision_alternatives(self, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        """
        q = """MATCH (case:Case:{label}) -[:Alternative]-> (alt:Alternative:{label}) WHERE id(case) = {case_id} RETURN alt.title AS title, id(alt) AS alt_id"""
        return [(result["title"], result["alt_id"]) for result in self.query(q, locals())]
    
    
    def change_alternative_property(self, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        q = """MATCH (alt:Alternative:{label}) WHERE id(alt) = {alternative} SET alt.{name} = "{value}" """
        self.query(q, locals())
        
    
    def get_alternative_property(self, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        try:
            q = """MATCH (alt:Alternative:{label}) WHERE id(alt) = {alternative} RETURN alt.{name} AS name"""
            return next(iter(self.query(q, locals())))["name"]
        except:
            return None