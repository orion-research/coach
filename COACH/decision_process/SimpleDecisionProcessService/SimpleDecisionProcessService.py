"""
An example of a decision process service. It implements a simple decision process in three steps:
1. Select an estimation method to be used to rank the value of alternatives.
2. For each alternative, estimate the value of each alternative.
3. Review the resulting ranking.
"""

<<<<<<< HEAD

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))
=======
# Add the grandparent directory to the module load path
import os
import sys
#sys.path.append(os.path.split(os.path.split(os.path.split(os.path.split(os.path.realpath(__file__))[0])[0])[0])[0])
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))
print(sys.path)
>>>>>>> c133459ddcee6be077fab5c4a581278c451e0da2


# Coach framework
from COACH.framework import coach

# Standard libraries
import json

# Web server framework
from flask import request, redirect
from flask.templating import render_template

import requests


class SimpleDecisionProcessService(coach.DecisionProcessService):

    def create_endpoints(self):
        # Initialize the API
        super(SimpleDecisionProcessService, self).create_endpoints()

        # States, represented by dialogues
        self.select_estimation_method_dialogue = self.create_state("select_estimation_method_dialogue.html")
        self.perform_ranking_dialogue = self.create_state("perform_ranking_dialogue.html")
        self.show_ranking_dialogue = self.create_state("show_ranking_dialogue.html")
        
        # Endpoints for transitions between the states without side effects
        self.ms.add_url_rule("/select_estimation_method_dialogue", view_func = self.select_estimation_method_dialogue_transition)
        self.ms.add_url_rule("/perform_ranking_dialogue", view_func = self.perform_ranking_dialogue_transition)
        self.ms.add_url_rule("/show_ranking_dialogue", view_func = self.show_ranking_dialogue_transition)
        
        # Endpoints for transitions between states with side effects
        self.ms.add_url_rule("/select_estimation_method", view_func = self.select_estimation_method, methods = ["POST"])
        self.ms.add_url_rule("/perform_ranking", view_func = self.perform_ranking, methods = ["POST"])


    def process_menu(self):
        try:
            return render_template("process_menu.html", url = request.url_root, case_id = request.values["case_id"])
        except Exception as e:
            self.ms.logger.error("Error in process_menu: " + str(e))
            return "Error in process_menu: Please check log file!"


    def select_estimation_method_dialogue_transition(self):
        """
        Endpoint which lets the user select which estimation method to use for this decision process.
        """
        root = request.values["root"]
        case_id = request.values["case_id"]
        # Fetch the available services from the directories available in the root.
        directories = json.loads(requests.get(root + "get_service_directories").text)
        services = []
        for d in directories:
            services += json.loads(requests.get(d + "/get_services?type=estimation_method").text)

        # Create the alternatives for a dropdown menu
        # TODO: It should show the current estimation method as preselected.
        
        options = ["<OPTION value=\"%s\"> %s </A>" % (s[2], s[1]) for s in services]

        # Render the dialogue
        return self.go_to_state(self.select_estimation_method_dialogue, estimation_methods = options, this_process = request.url_root, 
                                root = root, case_id = case_id)


    def perform_ranking_dialogue_transition(self):
        """
        Endpoint which lets the user rank each of the alternatives using the selected estimation method dialogue.
        """
        root = request.values["root"]
        case_id = request.values["case_id"]

        estimation_method = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "estimation_method"}).text

        if estimation_method:
            # Get the alternatives from root and build a list to be fitted into a dropdown menu
            decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
            options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]
        
            # Get the estimation method's dialogue
            estimation_dialogue = requests.get("http://" + estimation_method + "/dialogue").text
        
            # Render the dialogue
            return self.go_to_state(self.perform_ranking_dialogue, options = options, estimation_dialogue = estimation_dialogue, this_process = request.url_root,
                                    root = root, case_id = case_id, estimation_method = estimation_method)
        else:
            return "You need to select an estimation method before you can rank alternatives!"
        

    def show_ranking_dialogue_transition(self):
        """
        Endpoint which shows the alternatives in rank order. Unranked alternatives are at the bottom.
        """
        root = request.values["root"]
        case_id = request.values["case_id"]

        # Get the alternatives for the case.
        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
        
        # Get the estimate for each alternative.
        estimates = [(a[0], requests.get(root + "get_alternative_property", params = {"alternative": a[1], "name": "estimate"}).text) for a in decision_alternatives]

        # Sort the ranked alternatives.
        ranked_alternatives = sorted([(a, e) for (a, e) in estimates if e], key = lambda p: float(p[1]), reverse = True)
        unranked_alternatives = [a for (a, e) in estimates if not e]
        
        # Render the dialogue
        ranked_alternatives = [a + ": estimation = " + e for (a, e) in ranked_alternatives]
        unranked_alternatives = [a + ": no estimation" for a in unranked_alternatives]
        
        return self.go_to_state(self.show_ranking_dialogue, ranked = ranked_alternatives, unranked = unranked_alternatives)


    def select_estimation_method(self):
        """
        This method is called using POST when the user presses the select button in the select_estimation_method_dialogue.
        It gets to form parameters: root, which is the url of the root server, and method, which is the url of the selected estimation method.
        It changes the selection in the case database of the root server, and then returns a status message to be shown in the main dialogue window.
        """
        
        # Write the selection to the database.
        root = request.values["root"]
        method = request.values["method"]
        case_id = request.values["case_id"]
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "estimation_method", "value": method})

        message = requests.utils.quote("Estimation method changed to ") + method
        return redirect(root + "main_menu?message=" + message)
    
    
    def perform_ranking(self):
        """
        This method is called using POST when the user presses the button in the estimation method dialogue as part of the ranking dialogue.
        It calculates the estimate and writes it to the database and then returns a status message showing the updated estimate value in the main dialogue window.
        """
        
        root = request.values["root"]
        alternative = request.values["alternative"]
        case_id = request.values["case_id"]
        estimation_method = request.values["estimation_method"]

        # Calculate estimate. This is done by removing the values "root", "case_id", "estimation_method" and "alternative" from the dictionary of values. 
        # The rest should be estimation method arguments, and are passed to the evaluate endpoint of the estimation method.
        params = dict()
        for p in set(request.values.keys()) - {"root", "case_id", "estimation_method", "alternative"}:
            params[p] = request.values[p]
        value = requests.get("http://" + estimation_method + "/evaluate", params = params).text
    
        # Write estimate to the database
        # TODO: For now, just set it as an attribute of the alternative node. This needs to be improved!
        requests.post(root + "change_alternative_property", data = {"alternative": str(alternative), "name": "estimate", "value": value})
    
        message = requests.utils.quote("Estimate has been changed to ") + value
        return redirect(root + "main_menu?message=" + message)
    
    
if __name__ == '__main__':
    SimpleDecisionProcessService("settings/decision_process_settings.json")
