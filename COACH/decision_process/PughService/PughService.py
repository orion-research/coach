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
from flask import request
from flask.templating import render_template


class PughService(coach.DecisionProcessService):

    # Auxiliary functions

    def dictionary_to_string(self, dictionary):
        """
        Converts a dictionary to a string that can be stored as a property in the case database.
        """
        return json.dumps(dictionary)
    
    
    def string_to_dictionary(self, string):
        """
        Converts a string that has been stored as a property in the case database to a dictionary.
        """
        return json.loads(string)
    
    
    def get_criteria(self, user_id, delegate_token, case_db, case_id):
        """
        Queries the case_db service for the criteria associated with a certain case_id.
        It returns a dictionary, with criteria name as keys and weights as values.
        """
        case_db_proxy = self.create_proxy(case_db)
        criteria_string = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "criteria")
        if criteria_string:
            return self.string_to_dictionary(criteria_string)
        else:
            return dict()


    def set_criteria(self, user_id, delegate_token, case_db, case_id, criteria):
        """
        Sets the criteria associated with a certain case_id in the case_db service.
        Criteria is a dictionary, which is stored as a string.
        """
        case_db_proxy = self.create_proxy(case_db)
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "criteria", value = self.dictionary_to_string(criteria))
        

    def get_alternative_ranking(self, user_id, delegate_token, case_db, case_id, alternative_id):
        """
        Queries the case_db service for the ranking associated with a certain alternative_id.
        It returns a dictionary, with criteria name as keys and ranking for the alternative as values. 
        """
        case_db_proxy = self.create_proxy(case_db)
        alternative_ranking_string = case_db_proxy.get_alternative_property(user_id = user_id, token = delegate_token, case_id = case_id, alternative = alternative_id, name = "ranking")
        if alternative_ranking_string:
            return self.string_to_dictionary(alternative_ranking_string)
        else:
            return dict()
        

    def set_alternative_ranking(self, user_id, delegate_token, case_db, case_id, alternative_id, ranking):
        """
        Sets the ranking associated with a certain alternative_id in the case_db service.
        Ranking is a dictionary, which is stored as a string.
        """
        case_db_proxy = self.create_proxy(case_db)
        case_db_proxy.change_alternative_property(user_id = user_id, token = delegate_token, case_id = case_id, alternative = alternative_id, name = "ranking", 
                                                  value = self.dictionary_to_string(ranking))
        

    # Endpoints

    @endpoint("/process_menu", ["GET"], "text/html")
    def process_menu(self):
        return render_template("process_menu.html")


    @endpoint("/select_baseline_dialogue", ["GET"], "text/html")
    def select_baseline_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which lets the user select the baseline alternative.
        """
        # Get the decision alternatives from case_db and build a list to be fitted into a dropdown menu
        case_db_proxy = self.create_proxy(case_db)
        decision_alternatives = case_db_proxy.get_decision_alternatives(user_id = user_id, token = delegate_token, case_id = case_id)
        options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]

        # Render the dialogue
        return render_template("select_baseline_dialogue.html", alternatives = options)
        
    
    @endpoint("/select_baseline", ["POST"], "text/html")
    def select_baseline(self, user_id, delegate_token, case_db, baseline, case_id):
        """
        This method is called using POST when the user presses the select button in the select_baseline_dialogue.
        It gets two form parameters: case_db, which is the url of the case database server, and baseline, which is the id of the selected alternative.
        It changes the selection in the case database, and then shows the matrix dialogue.
        """
        # Write the selection to the database, and show a message
        case_db_proxy = self.create_proxy(case_db)
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "baseline", value = baseline)
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id)    
    
    
    @endpoint("/add_criterium_dialogue", ["GET"], "text/html")
    def add_criterium_dialogue_transition(self):
        """
        Endpoint which shows the dialogue for adding criteria.
        """
        return render_template("add_criterium_dialogue.html")
    
    
    @endpoint("/add_criterium", ["POST"], "text/html")
    def add_criterium(self, user_id, delegate_token, case_db, case_id, criterium, weight):
        """
        This method is called using POST when the user presses the select button in the add_criterium_dialogue.
        It gets three form parameters: case_db, which is the url of the case database server, and criterium, which is the name of the new criterium,
        and weight which is its weight. The criteria are stored in the case database as a string which represents a Python dictionary on json format,
        assigned to the criteria attribute of the case node. 
        """
        # Get the current set of criteria from the case database, add the new one to the set, and write it back to the database.
        criteria = self.get_criteria(user_id, delegate_token, case_db, case_id)
        criteria[criterium] = weight
        self.set_criteria(user_id, delegate_token, case_db, case_id, criteria)
            
        # Go to the matrix dialogue state
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id)    
    
    
    @endpoint("/change_criterium_dialogue", ["GET"], "text/html")
    def change_criterium_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which shows the dialogue for changing criteria.
        """
        criteria = self.get_criteria(user_id, delegate_token, case_db, case_id).keys()
        options = ["<OPTION value=\"%s\"> %s </A>" % (c, c) for c in criteria]
        
        return render_template("change_criterium_dialogue.html", criteria = options)
    
    
    @endpoint("/change_criterium", ["POST"], "text/html")
    def change_criterium(self, user_id, delegate_token, case_db, case_id, criterium, new_name, new_weight, action):
        """
        This method is called using POST when the user presses either the change criterium or delete criterium buttons in the 
        change_criterium_dialogue. The form parameters are case_db and case_id, the current name of the criterium to change, 
        optionally a new name and optionally a new weight. There are two submit buttons in the form, and the one selected is indicated
        in the button parameter. The method modifies the list of criteria in the root node, and also the ranking in each
        alternative. 
        """
        # Change or delete the criterium name in the list of criteria in the case node
        criteria = self.get_criteria(user_id, delegate_token, case_db, case_id)
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
        self.set_criteria(user_id, delegate_token, case_db, case_id, criteria)
        
        # Change or delete the criterium name and weight in the rankings in each alternative node
        case_db_proxy = self.create_proxy(case_db)
        decision_alternatives = case_db_proxy.get_decision_alternatives(user_id = user_id, token = delegate_token, case_id = case_id)
        alternative_ids = [a[1] for a in decision_alternatives]

        for a in alternative_ids:
            alternative_ranking = self.get_alternative_ranking(user_id, delegate_token, case_db, case_id, a)
            if criterium in alternative_ranking:
                if new_name and action == "Change criterium":
                    alternative_ranking[new_name] = alternative_ranking[criterium]
                    del alternative_ranking[criterium]
                elif action == "Delete criterium":
                    del alternative_ranking[criterium]
                self.set_alternative_ranking(user_id, delegate_token, case_db, case_id, a, alternative_ranking)
        
        return "Changed criterium!"
    
    
    @endpoint("/matrix_dialogue", ["GET"], "text/html")
    def matrix_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which shows the Pugh matrix dialogue.
        """
        # Get alternatives from the database
        case_db_proxy = self.create_proxy(case_db)
        decision_alternatives = case_db_proxy.get_decision_alternatives(user_id = user_id, token = delegate_token, case_id = case_id)
        alternatives = [a[0] for a in decision_alternatives]
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        weights = self.get_criteria(user_id, delegate_token, case_db, case_id)
        criteria = weights.keys()
        
        # Get rankings from the database
        ranking = dict()
        for a in alternative_ids:
            ranking[a] = self.get_alternative_ranking(user_id, delegate_token, case_db, case_id, a)
        
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
    
    
    @endpoint("/change_rating", ["POST"], "text/html")
    def change_rating(self, user_id, delegate_token, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the Pugh matrix dialogue. It updates the values
        of the ranking of each alternative according to the current values in the dialogue.
        """
        # Get alternatives from the database
        case_db_proxy = self.create_proxy(case_db)

        decision_alternatives = case_db_proxy.get_decision_alternatives(user_id = user_id, token = delegate_token, case_id = case_id)
        alternative_ids = [a[1] for a in decision_alternatives]
        
        # Get criteria from the database
        criteria = self.get_criteria(user_id, delegate_token, case_db, case_id).keys()

        # For each alternative, build a map from criteria to value and write it to the database
        for a in alternative_ids:
            ranking = { c : request.values[str(a) + ":" + c] for c in criteria }
            self.set_alternative_ranking(user_id, delegate_token, case_db, case_id, a, ranking)

        # Show the updated matrix        
        return self.matrix_dialogue_transition(user_id, delegate_token, case_db, case_id)    
        

if __name__ == '__main__':
    PughService(sys.argv[1]).run()