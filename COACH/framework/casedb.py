'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''


# Database connection
from neo4jrestclient.client import GraphDatabase


class CaseDatabase:
    
    """
    The case database provides the interface to the database for storing case information. It wraps an API around a standard graph DBMS.
    
    TODO: 
    - Probably, it is wise to use Neo4j's query language as much as possible, to minimize dependency
    on the rest library.
    - These actions should also generate entries into a history, showing who, when, and what has been done. 
    """

    def __init__(self, url, username, password):
        self._db = GraphDatabase(url, username = username, password = password)


    def users(self, user_id = None):
        """
        Queries the case database and returns an iterable of the users with the given id, or all users is no user_id is provided.
        
        TODO: replace with the following query:
        q = MATCH (u: User) WHERE u.user_id = %s RETURN u % user_id 
        q = MATCH (u: User) RETURN u 
        """
        try:
            if user_id:
                return self._db.labels.get("User").get(user_id = user_id)
            else:
                return self._db.labels.get("User").all()
        except:
            # Label did not exist, so create it and return the empty list
            self._db.labels.create("User")
            return []
    
    
    def user_cases(self, user_id):
        """
        user_cases queries the case database and returns a list of the cases connected to the user.
        Each case is represented by a pair indicating case id and case title.
        """
        q = """MATCH (case: Case) -[Stakeholder]-> (user {user_id: \"%s\"}) RETURN id(case), case.title""" % user_id
        return [(case_id, case_title) for (case_id, case_title) in self._db.query(q)]
        
    
    def create_user(self, user_id):
        """
        Creates a new user in the database, if it does not exist already.
        """
        if len(self.users(user_id)) == 0:
            new_user = self._db.nodes.create(user_id = user_id)
            new_user.labels.add("User")


    def create_case(self, title, description, initiator):
        """
        Creates a new case in the database, with a relation to the initiating user. It returns the database id of the new case.
        """
        new_case = self._db.nodes.create(title = title, description = description)
        new_case.labels.add("Case")
        
        # Mark the current user as a stakeholder and initiator of this decision case
        new_case.relationships.create("Stakeholder", initiator, role = "initiator")
        return new_case.id
        
    
    def change_case_description(self, case_id, title, description):
        """
        Changes the title and description fields of the case with case_id.
        """
        q = """MATCH (case: Case) WHERE id(case) = {case_id} SET case.title = \"{title}\", case.description = \"{description}\""""
        self._db.query(q.format(**locals()))
    
        
    def get_case_description(self, case_id):
        """
        Returns a tuple containing the case title and description for the case with case_id.
        """
        q = """MATCH (case:Case) WHERE id(case) = {case_id} RETURN case.title, case.description"""
        result = self._db.query(q.format(**locals()))[0]
        return (result[0], result[1])
        

    def add_stakeholder(self, user_id, case_id):    
        user_node = self._db.labels.get("User").get(user_id = user_id)[0]
        case_node = self._db.nodes[case_id]
        case_node.relationships.create("Stakeholder", user_node, role = "contributor")

    
    def create_alternative(self, title, description, case_id):
        """
        Creates a decision alternative and links it to the case.
        """
        case_node = self._db.nodes[case_id]
        new_alternative = self._db.nodes.create(title = title, description = description)
        new_alternative.labels.add("Alternative")
        case_node.relationships.create("Alternative", new_alternative)

    
    def get_decision_process(self, case_id):
        """
        Returns the decision process url of the case, or None if no decision process has been selected.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = %s RETURN case.decision_process LIMIT 1""" % case_id
            # Why is the result a list of lists????
            # Probably, because each return can contain several elements and hence they are gathered in a list
            return self._db.query(q)[0][0]
        except:
            return None
    
    
    def change_decision_process(self, case_id, url):
        """
        Changes the decision process url associated with a case.
        """

        q = """MATCH (case: Case) WHERE id(case) = %s SET case.decision_process = \"%s\"""" % (case_id, url)
        self._db.query(q)

    
    def change_case_property(self, case_id, name, value):
        """
        Changes the property name of the case_id node to become value.
        """
        q = """MATCH (case: Case) WHERE id(case) = %s SET case.%s = \"%s\"""" % (case_id, name, value)
        self._db.query(q)
        
    
    def get_case_property(self, case_id, name):
        """
        Gets the value of the property name of the case_id node, or None if it does not exist.
        """
        try:
            q = """MATCH (case: Case) WHERE id(case) = %s RETURN case.%s""" % (case_id, name)
            return self._db.query(q)[0][0]
        except:
            return None
        
    
    def get_decision_alternatives(self, case_id):
        """
        Gets the list of decision alternatives associated with the case_id node, returning both title and id.
        TODO: The query needs to be fixed. It does not check that the case is correct.
        """
#        q = """MATCH (case: Case) -[:Alternative]-> (alt: Alternative) WHERE id(case) = %s RETURN alt.title, id(alt)""" % (case_id,)
        q = """MATCH (case: Case) -[:Alternative]-> (alt: Alternative) WHERE id(case) = {case_id} RETURN alt.title, id(alt)""".format(**locals())
        return list(self._db.query(q))
    
    
    def change_alternative_property(self, alternative, name, value):
        """
        Changes the property name of the alternative node to become value.
        """
        q = """MATCH (alt: Alternative) WHERE id(alt) = %s SET alt.%s = \"%s\"""" % (alternative, name, value)
        self._db.query(q)
        
    
    def get_alternative_property(self, alternative, name):
        """
        Gets the value of the property name of the alternative node, or None if it does not exist.
        """
        try:
            q = """MATCH (alt: Alternative) WHERE id(alt) = %s RETURN alt.%s""" % (alternative, name)
            return self._db.query(q)[0][0]
        except:
            return None
        
    
