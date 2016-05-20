'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''


# Database connection
from neo4jrestclient.client import GraphDatabase


class CaseDatabase:
    
    """
    The case database provides the interface to the database for storing case information. 
    It wraps an API around a standard graph DBMS.
    
    TODO: 
    - All actions should generate entries into a history, showing who, when, and what has been done.
    This is useful for being able to analyze decision processes. 
    """

    def __init__(self, url, username, password):
        self._db = GraphDatabase(url, username = username, password = password)


    def query(self, q, context = {}):
        """
        Function encapsulating the query interface to the database.
        q is the query string, and context is an optional dictionary containing variables to be substituted into q.
        """
        return self._db.query(q.format(**context))


    def user_ids(self):
        """
        Queries the case database and returns an iterable of all user ids (the name the user uses to log in).
        q = MATCH (u: User) RETURN u 
        """
        q = """MATCH (u: User) RETURN u.user_id"""
        return [u for (u,) in self.query(q, locals())]
    
    
    def user_cases(self, user_id):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        q = """MATCH (case: Case) -[Stakeholder]-> (user {{user_id: "{user_id}"}}) RETURN id(case), case.title"""
        return [(case_id, case_title) for (case_id, case_title) in self.query(q, locals())]
        
    
    def create_user(self, user_id):
        """
        Creates a new user in the database. 
        """
        q = """CREATE (u: User {{user_id : "{user_id}"}})"""
        self.query(q, locals())
        

    def create_case(self, title, description, initiator):
        """
        Creates a new case in the database, with a relation to the initiating user (referenced by user_id). 
        It returns the database id of the new case.
        """

        # First create the new case node, and get it's id
        q1 = """CREATE (c: Case {{title: "{title}", description: "{description}"}}) RETURN id(c)"""
        case_id = self.query(q1, locals())[0][0]
        
        # Then create the relationship
        q2 = """\
        MATCH (c: Case), (u: User)
        WHERE id(c) = {case_id} AND u.user_id = "{initiator}"
        CREATE (c) -[: Stakeholder {{role: "initiator"}}]-> (u)
        """
        self.query(q2, locals())
        return case_id        
        
    
    def change_case_description(self, case_id, title, description):
        """
        Changes the title and description fields of the case with case_id.
        """
        q = """MATCH (case: Case) WHERE id(case) = {case_id} SET case.title = "{title}", case.description = "{description}" """
        self.query(q, locals())
           
        
    def get_case_description(self, case_id):
        """
        Returns a tuple containing the case title and description for the case with case_id.
        """
        q = """MATCH (case:Case) WHERE id(case) = {case_id} RETURN case.title, case.description"""
        result = self.query(q, locals())[0]
        return (result[0], result[1])
        

    def add_stakeholder(self, user_id, case_id, role = "contributor"):
        """
        Adds a user as a stakeholder with the provided role to the case. 
        """
        q = """\
        MATCH (c: Case), (u: User)
        WHERE id(c) = {case_id} AND u.user_id = "{user_id}"
        CREATE (c) -[: Stakeholder {{role: "{role}"}}]-> (u)
        """
        self.query(q, locals())

    
    def create_alternative(self, title, description, case_id):
        """
        Creates a decision alternative and links it to the case.
        """

        # First create the new alternative, and get it's id
        q1 = """CREATE (a: Alternative {{title: "{title}", description: "{description}"}}) RETURN id(a)"""
        new_alternative = self.query(q1, locals())[0][0]
        
        # Then create the relationship to the case
        q2 = """\
        MATCH (c: Case), (a: Alternative)
        WHERE id(c) = {case_id} AND id(a) = {new_alternative}
        CREATE (c) -[: Alternative]-> (a)
        """
        self.query(q2, locals())
        return case_id        

    
    def get_decision_process(self, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = {case_id} RETURN case.decision_process LIMIT 1"""
            return self.query(q, locals())[0][0]
        except:
            return None
    
    
    def change_decision_process(self, case_id, url):
        """
        Changes the decision process url associated with a case.
        """

        q = """MATCH (case: Case) WHERE id(case) = {case_id} SET case.decision_process = "{url}" """
        self.query(q, locals())

    
    def change_case_property(self, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        q = """MATCH (case: Case) WHERE id(case) = {case_id} SET case.{name} = "{value}\""""
        self.query(q, locals())
        
    
    def get_case_property(self, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = {case_id} RETURN case.{name}"""
            return self.query(q, locals())[0][0]
        except:
            return None
        
    
    def get_decision_alternatives(self, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        """
        q = """MATCH (case: Case) -[:Alternative]-> (alt: Alternative) WHERE id(case) = {case_id} RETURN alt.title, id(alt)"""
        return list(self.query(q, locals()))
    
    
    def change_alternative_property(self, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        q = """MATCH (alt: Alternative) WHERE id(alt) = {alternative} SET alt.{name} = "{value}" """
        self.query(q, locals())
        
    
    def get_alternative_property(self, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        try:
            q = """MATCH (alt: Alternative) WHERE id(alt) = {alternative} RETURN alt.{name}"""
            return self.query(q, locals())[0][0]
        except:
            return None
        
    
