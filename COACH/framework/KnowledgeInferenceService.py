'''
Created on 3 feb. 2017

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Standard libraries
import json

# Web service framework
from flask import Response, request

# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Semantic web framework
import rdflib


class KnowledgeInferenceService(coach.Microservice):
    
    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initiates the KnowledgeInferenceService.
        """
        super().__init__(settings_file_name, working_directory = working_directory)
        self.data_sources = {}
        self.graph = rdflib.Graph()


    @endpoint("/load_data", ["GET", "POST"])
    def load_data(self, url):
        """
        Loads data from the provided URL, and stores it in the graph.
        If the graph already contains data, the new data is added.
        
        Example data:
        https://jena.apache.org/tutorials/sparql_data/vc-db-1.rdf
        """
        self.graph.load(url)
        self.data_sources += { url }
        return Response("Ok")
    

    @endpoint("/clear_data", ["GET", "POST"])
    def clear_data(self):
        """
        Clears the data in the graph.
        """
        self.graph = rdflib.Graph()
        self.data_sources = { }
        return Response("Ok")
        
        
    @endpoint("/show_data", ["GET", "POST"])
    def show_data(self, format):
        """
        Returns the data in the current graph on the specified format (allowed values: json-ld, n3, nquads, nt, pretty-xml, trig, trix, turtle, xml).
        """
        result = self.graph.serialize(format = format)
        return Response(result)
    
    
    @endpoint("/query", ["GET", "POST"])
    def query_data(self, q):
        """
        Runs a query on the current graph. The query is expressed in SparQL.
        
        Example queries:
        SELECT ?x WHERE { ?x  <http://www.w3.org/2001/vcard-rdf/3.0#FN>  "John Smith" }
        """
        try:
            result = self.graph.query(q)
            print("Number of triples in result: " + str(len(result)))
            for triple in result:
                print(triple)
            return Response(json.dumps(list(result)))
        except Exception as e:
            return Response("Error: " + str(e))
        
        
    @endpoint("/test_dialogue", ["POST"])
    def test_dialogue(self, user_id, user_token):
        """
        Returns a test dialogue that can be used to try out queries. It has fields for the data sources, the query, and the results.
        If the data sources are not loaded, it first loads them, and then evaluates the query.
        """
        
        dialogue = """
<HTML>
<BODY>
<FORM action="/test_dialogue" method="post">
<H1>Test dialogue for Knowledge Inference Service queries</H1>
<INPUT type="submit" value="Evaluate">
<BR>
Data sources (semicolon separated): <BR>
<TEXTAREA name="data_sources" rows="10" cols="80">{data_sources}</TEXTAREA>

<BR>Query: <BR>
<TEXTAREA name="query" rows="10" cols="80">{query}</TEXTAREA>

<BR>Result: <BR>
{result}
</FORM>

</BODY>            
</HTML>
"""

        # Load data set from the case database for all cases which this user can access
        print(self.settings)
        case_db_proxy = self.create_proxy(self.get_setting("database"))
        cases = case_db_proxy.user_cases(user_id = user_id, user_token = user_token)
        for [c, _] in cases:
            try:
                print("Loading case data for case " + str(c))
                case_data = case_db_proxy.export_case_data(user_id = user_id, user_token = user_token, case_id = c, format = "n3")
                self.graph.parse(data = case_data, format = "n3")
            except Exception:
                print("Failed to load case data for case " + str(c))
            
        # Ensure that all datasets are loaded
        data_sources = request.values.get("data_sources", "")
        """
        data_sources_list = { ds.strip() for ds in request.values.get("data_sources", "").split(";") }
        if data_sources_list != self.data_sources:
            self.graph = rdflib.Graph()
            self.data_sources = { }
            for ds in data_sources_list:
                try:
                    self.graph.load(ds)
#                    self.data_sources += { ds }
                    print("Loaded " + ds)
                except Exception:
                    print("Could not load " + ds)
        """

        # Make the query        
        q = request.values.get("query", "")
        
        # The following query gives the id of all the user who work in any of the cases
        q = """
PREFIX orion: <https://github.com/orion-research/coach/tree/master/COACH/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX ns: <http://127.0.0.1#>

SELECT ?user_id
WHERE {
    ?user rdf:type orion:User .
    ?user orion:user_id ?user_id .
}
"""        
        try:
            print("Executing query: " + str(q))
            result = self.graph.query(q)
        except Exception as e:
            print("Could not execute query: " + str(e))
            result = []
        
        # Transform the result into a string
        result_text = " <BR> ".join([str(x) for x in result])
        
        return Response(dialogue.format(data_sources = data_sources, query = q, result = result_text))