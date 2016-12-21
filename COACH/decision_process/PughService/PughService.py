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
from COACH.framework.coach import endpoint

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class PughService(coach.DecisionProcessService):

    # Auxiliary functions
    
    def get_criteria(self, root, case_id):
        """
        Queries the root service for the criteria associated with a certain case_id.
        It returns a dictionary, with criteria name as keys and weights as values.
        """
        criteria = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "criteria"}).text
        if criteria:
            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
            return json.loads(criteria.replace("'", "\""))
        else:
            return dict()


    # Endpoints

    @endpoint("/select_baseline_dialogue", ["GET"])
    def select_baseline_dialogue_transition(self, root, case_id):
        """
        Endpoint which lets the user select the baseline alternative.
        """
        # Get the decision alternatives from root and build a list to be fitted into a dropdown menu
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]

        # Render the dialogue
        return render_template("select_baseline_dialogue.html", alternatives = options, this_process = request.url_root, 
                               root = root, case_id = case_id)
        
    
    @endpoint("/add_criterium_dialogue", ["GET"])
    def add_criterium_dialogue_transition(self, root, case_id):
        """
        Endpoint which shows the dialogue for adding criteria.
        """
        return render_template("add_criterium_dialogue.html", this_process = request.url_root, root = root, case_id = case_id)
    
    
    @endpoint("/change_criterium_dialogue", ["GET"])
    def change_criterium_dialogue_transition(self, root, case_id):
        """
        Endpoint which shows the dialogue for changing criteria.
        """
        criteria = self.get_criteria(root, case_id).keys()
        options = ["<OPTION value=\"%s\"> %s </A>" % (c, c) for c in criteria]
        
        return render_template("change_criterium_dialogue.html", this_process = request.url_root, root = root, case_id = case_id, criteria = options)
    
    
    @endpoint("/matrix_dialogue", ["GET"])
    def matrix_dialogue_transition(self, root, case_id):
        """
        Endpoint which shows the Pugh matrix dialogue.
        """
        # Get alternatives from the database
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        alternatives = [a[0] for a in decision_alternatives]
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        weights = self.get_criteria(root, case_id)
        criteria = weights.keys()
        
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
        return render_template("matrix_dialogue.html", this_process = request.url_root, root = root, case_id = case_id,
                               alternatives = alternatives, alternative_ids = alternative_ids, 
                               criteria = criteria, weights = weights, ranking = ranking, sums = sums)
    
    
    @endpoint("/select_baseline", ["POST"])
    def select_baseline(self, root, baseline, case_id):
        """
        This method is called using POST when the user presses the select button in the select_baseline_dialogue.
        It gets two form parameters: root, which is the url of the root server, and baseline, which is the id of the selected alternative.
        It changes the selection in the case database of the root server, and then shows the matrix dialogue.
        """
        # Write the selection to the database, and show a message
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "baseline", "value": baseline})
        return redirect(root + "main_menu?main_dialogue=" + request.url_root + "matrix_dialogue?case_id=" + str(case_id))
    
    
    @endpoint("/add_criterium", ["POST"])
    def add_criterium(self, root, case_id, criterium, weight):
        """
        This method is called using POST when the user presses the select button in the add_criterium_dialogue.
        It gets three form parameters: root, which is the url of the root server, and criterium, which is the name of the new criterium,
        and weight which is its weight. The criteria are stored in the case database as a dictionary assigned to the criteria attribute
        of the case node. 
        """
        # Get the current set of criteria from the case database, and add the new one to the set
        criteria = self.get_criteria(root, case_id)
        criteria[criterium] = weight
        
        # Write the updated set to the database
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "criteria", "value": str(criteria)})

        # Go to the matrix dialogue state
        return redirect(root + "main_menu?main_dialogue=" + request.url_root + "matrix_dialogue?case_id=" + str(case_id))
    
    
    @endpoint("/change_criterium", ["POST"])
    def change_criterium(self, root, case_id, criterium, new_name, new_weight, action):
        """
        This method is called using POST when the user presses either the change criterium or delete criterium buttons in the 
        change_criterium_dialogue. The form parameters are root and case_id, the current name of the criterium to change, 
        optionally a new name and optionally a new weight. There are two submit buttons in the form, and the one selected is indicated
        in the button parameter. The method modifies the list of criteria in the root node, and also the ranking in each
        alternative. 
        """
        # Change or delete the criterium name in the list of criteria in the case node
        criteria = self.get_criteria(root, case_id)
        if action == "Delete criterium":
            del criteria[criterium]
        else:
            if new_name and new_weight:
                # Name and weight has changed, so delete old entry and add new data
                criteria[new_name] = int(new_weight)
                del criteria[criterium]
            elif not new_name and new_weight:
                # Only weight has changed
                criteria[criterium] = int(new_weight)
            elif new_name and not new_weight:
                # Only name has changed
                criteria[new_name] = criteria[criterium]
                del criteria[criterium]
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "criteria", "value": str(criteria)})
        
        # Change or delete the criterium name and weight in the rankings in each alternative node
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        alternative_ids = [a[1] for a in decision_alternatives]

        for a in alternative_ids:
            alternative_rankings = requests.get(root + "get_alternative_property", params = {"alternative": a, "name": "ranking"}).text
            if alternative_rankings:
                # Json does not allow '...' as string delimiters, so they must be changed to "..." 
                ranking = json.loads(alternative_rankings.replace("'", "\""))
                if criterium in ranking:
                    if new_name and action == "Change criterium":
                        ranking[new_name] = ranking[criterium]
                        del ranking[criterium]
                    elif action == "Delete criterium":
                        del ranking[criterium]
                    requests.post(root + "change_alternative_property", data = {"alternative": str(a), "name": "ranking", "value": str(ranking)})
        
        return redirect(root + "main_menu?message=Changed criterium!")
    
    
    @endpoint("/change_rating", ["POST"])
    def change_rating(self, root, case_id):
        """
        This method is called using POST when the user presses the save button in the Pugh matrix dialogue. It updates the values
        of the ranking of each alternative according to the current values in the dialogue.
        """
        # Get alternatives from the database
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = self.get_criteria(root, case_id).keys()

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