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
from COACH.framework.coach import endpoint, get_service, post_service

# Standard libraries
import json

# Web server framework
from flask import request
from flask.templating import render_template


class PughService(coach.DecisionProcessService):

    # Auxiliary functions
    
    def get_criteria(self, case_db, case_id):
        """
        Queries the case_db service for the criteria associated with a certain case_id.
        It returns a dictionary, with criteria name as keys and weights as values.
        """
        criteria = get_service(case_db, "get_case_property", case_id = case_id, name = "criteria")
        if criteria:
            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
            return json.loads(criteria.replace("'", "\""))
        else:
            return dict()


    # Endpoints

    @endpoint("/process_menu", ["GET"])
    def process_menu(self):
        return render_template("process_menu.html")


    @endpoint("/select_baseline_dialogue", ["GET"])
    def select_baseline_dialogue_transition(self, case_db, case_id):
        """
        Endpoint which lets the user select the baseline alternative.
        """
        # Get the decision alternatives from case_db and build a list to be fitted into a dropdown menu
        decision_alternatives = json.loads(get_service(case_db, "get_decision_alternatives", case_id = case_id))
        options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]

        # Render the dialogue
        return render_template("select_baseline_dialogue.html", alternatives = options)
        
    
    @endpoint("/select_baseline", ["POST"])
    def select_baseline(self, case_db, baseline, case_id):
        """
        This method is called using POST when the user presses the select button in the select_baseline_dialogue.
        It gets two form parameters: case_db, which is the url of the case database server, and baseline, which is the id of the selected alternative.
        It changes the selection in the case database, and then shows the matrix dialogue.
        """
        # Write the selection to the database, and show a message
        post_service(case_db, "change_case_property", case_id = str(case_id), name = "baseline", value = baseline)
        return self.matrix_dialogue_transition(case_db, case_id)    
    
    
    @endpoint("/add_criterium_dialogue", ["GET"])
    def add_criterium_dialogue_transition(self):
        """
        Endpoint which shows the dialogue for adding criteria.
        """
        return render_template("add_criterium_dialogue.html")
    
    
    @endpoint("/add_criterium", ["POST"])
    def add_criterium(self, case_db, case_id, criterium, weight):
        """
        This method is called using POST when the user presses the select button in the add_criterium_dialogue.
        It gets three form parameters: case_db, which is the url of the case database server, and criterium, which is the name of the new criterium,
        and weight which is its weight. The criteria are stored in the case database as a dictionary assigned to the criteria attribute
        of the case node. 
        """
        # Get the current set of criteria from the case database, and add the new one to the set
        criteria = self.get_criteria(case_db, case_id)
        criteria[criterium] = weight
        
        # Write the updated set to the database
        post_service(case_db, "change_case_property", case_id = str(case_id), name = "criteria", value = str(criteria))

        # Go to the matrix dialogue state
        return self.matrix_dialogue_transition(case_db, case_id)    
    
    
    @endpoint("/change_criterium_dialogue", ["GET"])
    def change_criterium_dialogue_transition(self, case_db, case_id):
        """
        Endpoint which shows the dialogue for changing criteria.
        """
        criteria = self.get_criteria(case_db, case_id).keys()
        options = ["<OPTION value=\"%s\"> %s </A>" % (c, c) for c in criteria]
        
        return render_template("change_criterium_dialogue.html", criteria = options)
    
    
    @endpoint("/change_criterium", ["POST"])
    def change_criterium(self, case_db, case_id, criterium, new_name, new_weight, action):
        """
        This method is called using POST when the user presses either the change criterium or delete criterium buttons in the 
        change_criterium_dialogue. The form parameters are case_db and case_id, the current name of the criterium to change, 
        optionally a new name and optionally a new weight. There are two submit buttons in the form, and the one selected is indicated
        in the button parameter. The method modifies the list of criteria in the root node, and also the ranking in each
        alternative. 
        """
        # Change or delete the criterium name in the list of criteria in the case node
        criteria = self.get_criteria(case_db, case_id)
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
        post_service(case_db, "change_case_property", case_id = str(case_id), name = "criteria", value = str(criteria))
        
        # Change or delete the criterium name and weight in the rankings in each alternative node
        decision_alternatives = json.loads(get_service(case_db, "get_decision_alternatives", case_id = case_id))
        alternative_ids = [a[1] for a in decision_alternatives]

        for a in alternative_ids:
            alternative_rankings = get_service(case_db, "get_alternative_property", alternative = a, name = "ranking")
            if alternative_rankings:
                # Json does not allow '...' as string delimiters, so they must be changed to "..." 
                ranking = json.loads(alternative_rankings.replace("'", "\""))
                if criterium in ranking:
                    if new_name and action == "Change criterium":
                        ranking[new_name] = ranking[criterium]
                        del ranking[criterium]
                    elif action == "Delete criterium":
                        del ranking[criterium]
                    post_service(case_db, "change_alternative_property", alternative = str(a), name = "ranking", value = str(ranking))
        
        return "Changed criterium!"
    
    
    @endpoint("/matrix_dialogue", ["GET"])
    def matrix_dialogue_transition(self, case_db, case_id):
        """
        Endpoint which shows the Pugh matrix dialogue.
        """
        # Get alternatives from the database
        decision_alternatives = json.loads(get_service(case_db, "get_decision_alternatives", case_id = case_id))
        alternatives = [a[0] for a in decision_alternatives]
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        weights = self.get_criteria(case_db, case_id)
        criteria = weights.keys()
        
        # Get rankings from the database
        ranking = dict()
        for a in alternative_ids:
            alternative_rankings = get_service(case_db, "get_alternative_property", alternative = a, name = "ranking")
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
        return render_template("matrix_dialogue.html", alternatives = alternatives, alternative_ids = alternative_ids, 
                               criteria = criteria, weights = weights, ranking = ranking, sums = sums)
    
    
    @endpoint("/change_rating", ["POST"])
    def change_rating(self, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the Pugh matrix dialogue. It updates the values
        of the ranking of each alternative according to the current values in the dialogue.
        """
        # Get alternatives from the database
        decision_alternatives = json.loads(get_service(case_db, "get_decision_alternatives", case_id = case_id))
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = self.get_criteria(case_db, case_id).keys()

        # For each alternative, build a map from criteria to value and write it to the database
        for a in alternative_ids:
            ranking = { c : request.values[str(a) + ":" + c] for c in criteria }
            post_service(case_db, "change_alternative_property", alternative = str(a), name = "ranking", value = str(ranking))

        # Show the updated matrix        
        return self.matrix_dialogue_transition(case_db, case_id)    
        

if __name__ == '__main__':
    PughService(sys.argv[1]).run()