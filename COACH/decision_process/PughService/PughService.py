'''
Created on 9 aug. 2016

@author: Jakob Axelsson
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

# Coach framework
from COACH.framework import coach

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class PughService(coach.DecisionProcessService):

    def create_endpoints(self):
        # Initialize the API
        super(PughService, self).create_endpoints()

        # States, represented by dialogues
        self.select_baseline_dialogue = self.create_state("select_baseline_dialogue.html")
        self.matrix_dialogue = self.create_state("matrix_dialogue.html")
        self.add_criterium_dialogue = self.create_state("add_criterium_dialogue.html")
        self.change_criterium_dialogue = self.create_state("change_criterium_dialogue.html")
        
        # Endpoints for transitions between the states without side effects
        self.ms.add_url_rule("/select_baseline_dialogue", view_func = self.select_baseline_dialogue_transition)
        self.ms.add_url_rule("/add_criterium_dialogue", view_func = self.add_criterium_dialogue_transition)
        self.ms.add_url_rule("/change_criterium_dialogue", view_func = self.change_criterium_dialogue_transition)
        self.ms.add_url_rule("/matrix_dialogue", view_func = self.matrix_dialogue_transition)
        
        # Endpoints for transitions between states with side effects
        self.ms.add_url_rule("/select_baseline", view_func = self.select_baseline, methods = ["POST"])
        self.ms.add_url_rule("/add_criterium", view_func = self.add_criterium, methods = ["POST"])
        self.ms.add_url_rule("/change_criterium", view_func = self.change_criterium, methods = ["POST"])
        self.ms.add_url_rule("/change_rating", view_func = self.change_rating, methods = ["POST"])
        

    def select_baseline_dialogue_transition(self):
        """
        Endpoint which lets the user select the baseline alternative.
        """
        root = request.values["root"]
        case_id = request.values["case_id"]
        
        # Get the decision alternatives from root and build a list to be fitted into a dropdown menu
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]

        # Render the dialogue
        return self.go_to_state(self.select_baseline_dialogue, alternatives = options, this_process = request.url_root, 
                                root = root, case_id = case_id)
    
    
    def add_criterium_dialogue_transition(self):
        root = request.values["root"]
        case_id = request.values["case_id"]
        return self.go_to_state(self.add_criterium_dialogue, this_process = request.url_root, root = root, case_id = case_id)
    
    
    def change_criterium_dialogue_transition(self):
        return "Not yet implemented!"
    
    
    def matrix_dialogue_transition(self):
        root = request.values["root"]
        case_id = request.values["case_id"]

        # Get alternatives from the database
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        alternatives = [a[0] for a in decision_alternatives]
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "criteria"}).text
        if criteria:
            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
            weights = json.loads(criteria.replace("'", "\""))
            criteria = weights.keys()
        else:
            criteria = []
            weights = dict()

        # Get rankings from the database
        ranking = dict()
        for a in alternative_ids:
            alternative_rankings = requests.get(root + "get_alternative_property", params = {"alternative": a, "name": "ranking"}).text
            if alternative_rankings:
                # Json does not allow '...' as string delimiters, so they must be changed to "..." 
                ranking[a] = json.loads(alternative_rankings.replace("'", "\""))
            else:
                ranking[a] = dict()
        
        # Set default value to zero for missing rankings
        for a in alternative_ids:
            for c in criteria:
                if c not in ranking[a]:
                    ranking[a][c] = 0
        
        # Calculate the evaluation sums
        sums = [sum([int(weights[c]) * int(r) for (c, r) in ranking[a].items()]) for a in alternative_ids]
        
        # Render the dialogue        
        return self.go_to_state(self.matrix_dialogue, this_process = request.url_root, root = root, case_id = case_id,
                                alternatives = alternatives, alternative_ids = alternative_ids, 
                                criteria = criteria, weights = weights, ranking = ranking, sums = sums)
    
    
    def select_baseline(self):
        """
        This method is called using POST when the user presses the select button in the select_baseline_dialogue.
        It gets two form parameters: root, which is the url of the root server, and baseline, which is the id of the selected alternative.
        It changes the selection in the case database of the root server, and then shows the matrix dialogue.
        """
        
        root = request.values["root"]
        baseline = request.values["baseline"]
        case_id = request.values["case_id"]

        # Write the selection to the database.
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "baseline", "value": baseline})

        # Go to the matrix dialogue state
        return redirect(root + "main_menu?main_dialogue=" + request.url_root + "matrix_dialogue?case_id=" + str(case_id))
    
    
    def add_criterium(self):
        """
        This method is called using POST when the user presses the select button in the add_criterium_dialogue.
        It gets three form parameters: root, which is the url of the root server, and criterium, which is the name of the new criterium,
        and weight which is its weight. The criteria are stored in the case database as a dictionary assigned to the criteria attribute
        of the case node. 
        """
        root = request.values["root"]
        case_id = request.values["case_id"]
        criterium = request.values["criterium"]
        weight = request.values["weight"]

        # Get the current set of criteria from the case database, and add the new one to the set
        criteria = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "criteria"}).text
        if criteria:
            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
            criteria = json.loads(criteria.replace("'", "\""))
            criteria[criterium] = weight
        else:
            criteria = { criterium : weight }
        
        # Write the updated set to the database
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "criteria", "value": str(criteria)})

        # Go to the matrix dialogue state
        return redirect(root + "main_menu?main_dialogue=" + request.url_root + "matrix_dialogue?case_id=" + str(case_id))
    
    
    def change_criterium(self):
        return "Not yet implemented!"
    
    
    def change_rating(self):
        root = request.values["root"]
        case_id = request.values["case_id"]

        # Get alternatives from the database
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "criteria"}).text
        if criteria:
            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
            criteria = json.loads(criteria.replace("'", "\"")).keys()
        else:
            criteria = []

        # For each alternative, build a map from criteria to value and write it to the database
        for a in alternative_ids:
            ranking = { c : request.values[str(a) + ":" + c] for c in criteria }
            requests.post(root + "change_alternative_property", data = {"alternative": str(a), "name": "ranking", "value": str(ranking)})
        
        # Show a message that the data has changed
        return redirect(root + "main_menu?message=Pugh analysis matrix updated")
        

    def process_menu(self):
        try:
            return render_template("process_menu.html", url = request.url_root, case_id = request.values["case_id"])
        except Exception as e:
            self.ms.logger.error("Error in process_menu: " + str(e))
            return "Error in process_menu: Please check log file!" + str(e) + str(request.values)


if __name__ == '__main__':
    PughService(sys.argv[1]).run()