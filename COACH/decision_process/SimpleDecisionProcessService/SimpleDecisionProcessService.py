"""
An example of a decision process service. It implements a simple decision process in three steps:
1. Select an estimation method to be used to rank the value of alternatives.
2. For each alternative, estimate the value of each alternative.
3. Review the resulting ranking.
"""

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


class SimpleDecisionProcessService(coach.DecisionProcessService):

    def process_menu(self):
        try:
            return render_template("process_menu.html", url = request.url_root, case_id = request.values["case_id"])
        except Exception as e:
            self.ms.logger.error("Error in process_menu: " + str(e))
            return "Error in process_menu: Please check log file!" + str(e) + str(request.values)


    @endpoint("/select_estimation_method_dialogue", ["GET"])
    def select_estimation_method_dialogue_transition(self, root, case_id):
        """
        Endpoint which lets the user select which estimation method to use for this decision process.
        """
        # Fetch the available services from the directories available in the root.
        directories = json.loads(requests.get(root + "get_service_directories").text)
        services = []
        for d in directories:
            services += json.loads(requests.get(self.get_setting("protocol") + "://" + d + "/get_services?type=estimation_method").text)

        # Create the alternatives for a dropdown menu
        # TODO: It should show the current estimation method as preselected.
        
        options = ["<OPTION value=\"%s\"> %s </A>" % (s[2], s[1]) for s in services]

        # Render the dialogue
        return render_template("select_estimation_method_dialogue.html", estimation_methods = options, this_process = request.url_root, 
                               root = root, case_id = case_id)


    @endpoint("/perform_ranking_dialogue", ["GET"])
    def perform_ranking_dialogue_transition(self, root, case_id):
        """
        Endpoint which lets the user rank each of the alternatives using the selected estimation method dialogue.
        """
        print(root)
        print(case_id)
        estimation_method = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "estimation_method"}).text

        if estimation_method:
            # Get the alternatives from root and build a list to be fitted into a dropdown menu
            decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
            options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]
        
            # Get the estimation method's dialogue
            estimation_dialogue = requests.get(self.get_setting("protocol") + "://" + estimation_method + "/dialogue").text
        
            return render_template("perform_ranking_dialogue.html", options = options, estimation_dialogue = estimation_dialogue, 
                                   this_process = self.get_setting("protocol") + "://" + self.host + ":" + str(self.port) + "/",
                                   root = root, case_id = case_id, estimation_method = estimation_method)
        else:
            return "You need to select an estimation method before you can rank alternatives!"
        

    @endpoint("/show_ranking_dialogue", ["GET"])
    def show_ranking_dialogue_transition(self, root, case_id):
        """
        Endpoint which shows the alternatives in rank order. Unranked alternatives are at the bottom.
        """
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
        return render_template("show_ranking_dialogue.html", ranked = ranked_alternatives, unranked = unranked_alternatives)


    @endpoint("/select_estimation_method", ["POST"])
    def select_estimation_method(self, root, method, case_id):
        """
        This method is called using POST when the user presses the select button in the select_estimation_method_dialogue.
        It gets to form parameters: root, which is the url of the root server, and method, which is the url of the selected estimation method.
        It changes the selection in the case database of the root server, and then returns a status message to be shown in the main dialogue window.
        """
        # Write the selection to the database.
        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "estimation_method", "value": method})

        message = requests.utils.quote("Estimation method changed to ") + method
        return redirect(root + "main_menu?message=" + message)
    
    
    @endpoint("/perform_ranking", ["POST"])
    def perform_ranking(self, root, alternative, case_id, estimation_method):
        """
        This method is called using POST when the user presses the button in the estimation method dialogue as part of the ranking dialogue.
        It calculates the estimate and writes it to the database and then returns a status message showing the updated estimate value in the main dialogue window.
        """
        # Calculate estimate. This is done by removing the values "root", "case_id", "estimation_method" and "alternative" from the dictionary of values. 
        # The rest should be estimation method arguments, and are passed to the evaluate endpoint of the estimation method.
        params = dict()
        for p in set(request.values.keys()) - {"root", "case_id", "estimation_method", "alternative"}:
            params[p] = request.values[p]
        value = requests.get(self.get_setting("protocol") + "://" + estimation_method + "/evaluate", params = params).text
    
        # Write estimate to the database
        # TODO: For now, just set it as an attribute of the alternative node. This needs to be improved!
        requests.post(root + "change_alternative_property", data = {"alternative": str(alternative), "name": "estimate", "value": value})
    
        message = requests.utils.quote("Estimate has been changed to ") + value
        return redirect(root + "main_menu?message=" + message)
    
    
if __name__ == '__main__':
    SimpleDecisionProcessService(sys.argv[1]).run()
