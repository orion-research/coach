# Tutorial for creating new decision process services

This tutorial will explain how to create a new decision process service.
The tutorial will be using the Pugh analysis service as an example.
It assumes that you have installed COACH locally according to the installation instructions.

# Creating an initial service class and hooking it up

In the COACH architecture, the different components are implemented as separate microservices, i.e.
small programs that are independent of each other. So to create a new decision process service,
you need to create such a new microservice. However, you also need to provide different information
that tells the runtime system how the different components fit together, depending on if the 
context is a stand-alone implementation on a local machine, or running on a server through Apache.
This necessary information is provided on a number of different files whose format are decided by
the implementation environment. However, the creation of these files is error-prone.

In order to facilitate the creation of new services as well as deployments, a script has been created.
In order to create a new service, a little bit of information is added in this script, and when it is
executed, the rest is automatically generated.

The script is located in the COACH top directory, and is called `build_coach_deployments`. In that script,
add the following line to declare the new Pugh analysis service:

	pugh = DecisionProcessService("PughService", "Pugh analysis", "decision_process.PughService")

The first argument is the class name used for the service; the second is a plain text description; and the
third is the path to where the module containing the class is to be stored.

Then modify the list of services to be listed in the service directory by adding `pugh`to it:  

	services_listed_in_directory = [simple, pugh, average_of_two, expert_opinion]

Finally, add `pugh` to the list of services and their ports, while adding a port which is not yet used by any other service.

	services_with_ports = {directory : 5003, 
	                       context_model : 5006, 
	                       knowledge_repository : 5005, 
	                       simple : 5002, 
	                       pugh : 5007, 
	                       average_of_two : 5004, 
	                       expert_opinion : 5001}

Now execute the script, by the command `python build_coach_deployments` (on some systems, you need to use `python3` instead of `python`).

You will get a list of messages on the screen, indicating which files have been modified by the script. One of the files is `PughService.py`
which is the file we will edit to implement the new service. If you are using Eclipse, you need to import this file, by right-clicking on
the folder `decision_process` and selecting `Refresh`. The contents of the file is as follows:

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
	
            @endpoint("/process_menu", ["GET"])
	    def process_menu(self):
	        return "Automatically generated process menu for PughService"
	        
	if __name__ == '__main__':
	        PughService(sys.argv[1]).run()


The file sets up the libraries that are needed for implementing the service. 
The only method that is required in a DecisionProcessService subclass is process_menu,
and in the code above, a temporary dummy for that has been added. 

(It can be convenient to be able to run your service as a stand alone program, and this is the purpose of the last two lines in the file.)

Now you have all you need to actually execute the service and it should be properly hooked up to the rest of the system. 
It is possible to run the service stand-alone. Execute `PughService.py` as a Python script
and supply the path to the local_settings.json file as a command line argument. This should
result in a message similar to this:

	 * Running on http://127.0.0.1:5007/ (Press CTRL+C to quit)

Now, start your web browser and point it to the address `http://127.0.0.1:5007/process_menu`,
and you should see "Automatically generated process menu for PughService" on your screen.

There is also a feature which allows you to test all endpoints through an interactive interface. 
It is available at `http://127.0.0.1:5007/test_ui`. As we add more endpoints, you may return to
this page to check that they have been properly added.

# Running the decision method as part of COACH locally

To start COACH locally, it is convenient to have a way of starting all services at once,
and this is handled by the script `launch_local.py` in the COACH top folder. 
You first need to start Neo4j and then run launch_local.py.
Use your browser to open 127.0.0.1:5000, then log in to COACH, open or create a decision case,
and select "Change decision process". In the menu you get, your new service should appear.
Select it, an then press "Select", and the line "Automatically generated process menu for PughService" 
should appear at the bottom left of the screen.

You are now ready to start developing the logic of your decision process.

# How COACH decision process services work

The interactions in COACH can best be visualized through a state machine. A state in that machine
is represented by a particular screen dialogue. Therefore, typically, there is a HTML
template file associated with each state, which is complemented by adding data dynamically
from the case database.

Transitions are triggered by user interactions, such as clicking a link or pressing a button,
either in the process menu or in the dialogue. 
These interactions are sent to the service by invoking a URL, and these URLs are captured 
using something called endpoints. The endpoints are implemented as Python functions.
The decorator `@endpoint` preceeding the method definition is the mechanism
used to indicate that this is a microservice endpoint, and the URL used to reach it is indicated together with the list of HTTP methods
that should be supported, as shown in the first instance of our class listed above.


So the steps you need to take when implementing your decision process are:
1. Design the state machine and transitions.
2. For each state, create an HTML template showing the dialogue.
3. For each transition, write a Python function and declare it as an endpoint using the `@endpoint` decorator.

# Process logic for the example decision process service

The Pugh analysis decision process is based on a comparison matrix, where each column
represents a decision alternative, and each row a comparison criteria. One alternative
is selected as a baseline, given a neutral rating for each criteria, and the decision 
makers then rate each other alternative against the baseline, with a score of + (better),
- (worse), or 0 (similar). The ratings are filled into the matrix, and the sum of ratings
are calculated at the bottom of the matrix. Optionally, the critera can be assigned
weights to distinguish their importance.

## State machine description

We will implement this process with four states: 
* The initial state lets the user select the baseline alternative. Note that defining 
alternatives is part of the generic COACH framework, and does not have to be dealt with here. 
(We will not deal with the possibility of changing the baseline as part of this tutorial.) 
* The main state displays the Pugh analysis matrix.
* To add new criterium, a dialogue is needed.
* Also, to change the name or weight or a criterium, or remove it, another dialogue is needed.
* Finally, a message state is used to show messages as a result of actions.

The transitions are:
* A transition from any state to the select baseline state. This is triggered from the process
menu.
* A transition from the select baseline state to the message state, with the side
effect of saving the selected baseline to the case database. This is triggered by a button
in the dialogue.
* A transition from any state to the add criterium state. This is triggered
from the process menu.
* A transition from the add criterium state to the message state, with the side
effect of adding the criterium to the case database. This is triggered by a button in the 
dialogue.
* A transition from any state to the change criterium state. This is triggered
from the process menu.
* A transition from the change criterium state to the message state, with the side
effect of changing or removing the criterium to the case database. This is triggered by
a button in the dialogue.
* A transition from the matrix dialogue state to the message state, with the side effect of changing
the rating in a cell in the matrix. This is triggered by a Javascript function embedded in the
dialogue, which in turn is triggered when the user makes a choice in the dropdown menu
in the cell.
* A transition from any state to the matrix dialogue state. This is triggered from the process menu.


## Process menu

We will now put the process menu in place. It requires an update of the process_menu method:

            @endpoint("/process_menu", ["GET"])
	    def process_menu(self):
	        try:
	            return render_template("process_menu.html", url = request.url_root, case_id = request.values["case_id"])
	        except Exception as e:
	            self.ms.logger.error("Error in process_menu: " + str(e))
	            return "Error in process_menu: Please check log file!" + str(e) + str(request.values)

It will try to render the HTML template that we define for the process menu. The rendering function
is passed a number of additional arguments, and these declare variables that can be accessed inside
the templates to add dynamic data to it. In this case, we pass the url of the caller and the case id.
If the rendering fails, we log the error and displays it to the user.

In the same folder as `PughService.py`, create a directory called `templates`. This will contain the html templates
that are used to generate the user interface of the service.

The HTML template for the process menu should be stored as `templates/process_menu.html` and will look like follows: 

	<LI><A HREF="/main_menu?main_dialogue={{url}}select_baseline_dialogue?case_id={{ case_id | safe }}">Select baseline</A></LI>
	<LI><A HREF="/main_menu?main_dialogue={{url}}add_criterium_dialogue?case_id={{ case_id | safe }}">Add criterium</A></LI>
	<LI><A HREF="/main_menu?main_dialogue={{url}}change_criterium_dialogue?case_id={{ case_id | safe }}">Change criterium</A></LI>
	<LI><A HREF="/main_menu?main_dialogue={{url}}matrix_dialogue?case_id={{ case_id | safe }}">Pugh matrix</A></LI>

Each line is a list item representing a menu choice, that just triggers the corresponding
endpoints. The double curly braces `{{ ... }}` are used to insert the parameters that were 
supplied to the rendering function. (For more details on the template syntax,
look up documentation on the Jinja2 template engine, which is used by the Flask
web framework that COACH employs.)

The HTML template refers to a number of new endpoints representing states, and these have to be provided. Therefore, for the time being,
we just add stubs for the triggering methods:

            @endpoint("/select_baseline_dialogue", ["GET"])
            def select_baseline_dialogue_transition(self):
                return "Not yet implemented!"
            
            @endpoint("/add_criterium_dialogue", ["GET"])
            def add_criterium_dialogue_transition(self):
                return "Not yet implemented!"
            
            @endpoint("/change_criterium_dialogue", ["GET"])
            def change_criterium_dialogue_transition(self):
                return "Not yet implemented!"
            
            @endpoint("/matrix_dialogue", ["GET"])
            def matrix_dialogue_transition(self):
                return "Not yet implemented!"

You can now restart the COACH local implementation, and check that the process menu works.

## Decision service data storage

Before starting to implement the different endpoint methods that do the actual work, it must
be decided how data associated with the particular decision service should be stored in the
case database. This needs to be done through the API of the root service, since the case
database is hidden behind that service, and currently this API gives two options: either
to store data as attributes of the case node, or as attributes of the alternatives.

In the Pugh service, the data will consist of a list of criteria each associated with a weight.
These will be stored as dictionaries with the criterium name as the key and weight as the value,
in the attribute criteria of the case node. Further, the data consists of the rating of
each alternative for each criteria, and this will be stored again as a dictionary in each
alternative node, with criteria as keys and the actual ratings as values.

Finally, it must be stored which alternative is the baseline, and we do that through an
attribute in the case node.

## Select baseline dialogue and transitions

To implement the selection of a baseline, a HTML template for the dialogue is needed
in the file `templates/select_baseline_dialogue`:

	<H2>Select a baseline</H2>
	
	<FORM action="{{this_process | safe}}select_baseline" method="post">
	<SELECT name="baseline">
	{% for a in alternatives %}
	{{ a | safe }}
	{% endfor %}
	</SELECT>
	<INPUT type="hidden" name="root" value="{{root | safe}}"/>
	<INPUT type="hidden" name="case_id" value="{{case_id | safe}}"/>
	<INPUT type="submit" value="Select"/>
	</FORM>

This dialogue consists of a form with a dropdown menu and a select button.
The action of the form is to call the select_baseline endpoint of our decision process 
using the POST method.
The alternatives in the menu are filled in from the alternatives variable provided
when calling the template rendering function.
The two hidden inputs are used to transfer data regarding the root service url
and the case id to the select_baseline endpoint. This is necessary, since the COACH
framework is based on the stateless REST concept, i.e., all required data has to
be passed to the endpoint every time.

To render this dialogue, the endpoint method select_baseline_dialogue_transition needs to be
implemented:

            @endpoint("/select_baseline_dialogue", ["GET"])
            def select_baseline_dialogue_transition(self, root, case_id):
	        """
	        Endpoint which lets the user select the baseline alternative.
	        """
	        # Get the decision alternatives from root and build a list to be fitted into a dropdown menu
	        decision_alternatives = json.loads(requests.get(root + "get_decision_alternatives", params = {"case_id": case_id}).text)
	        options = ["<OPTION value=\"%s\"> %s </A>" % (a[1], a[0]) for a in decision_alternatives]

	        # Render the dialogue
	        return self.go_to_state(self.select_baseline_dialogue, alternatives = options, this_process = request.url_root, 
	                                root = root, case_id = case_id)

Note that the method now takes two arguments, root and case_id. These are automatically bound to the values supplied in the http
request (in this case as GET parameters, in a URL call similar to `.../select_baseline_dialogue?root="..."&case_id=xxx`, but the
same mechanism also works for POST parameters present in a form element in the HTML page).

The decision alternatives to choose from are stored in the case database, which is held by
the root service. Therefore, a request for this data has to be made in order to build
the list of alternatives.

When the user has chosen a baseline in the menu, and presses the select button, the
select_baseline endpoint gets invoked. Its method is as follows:

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

It writes the id of the selected alternative to the case database as a property of the case node, and then shows a message.


## Add criterium dialogue and transitions

The add criterium dialogue is fairly similar to the select baseline, except that it contains
a text field for the name of the criterion, and a numerical field for its weight.
The file `templates\add_criterium_dialogue.html` should contain:

	<H2>Add a criterium</H2>
	
	<FORM action="{{this_process | safe}}add_criterium" method="post">
	Name: 
	<BR>
	<INPUT type="text" name="criterium" required>
	<BR>
	Weight:
	<BR>
	<INPUT type="number" name="weight" value="1" min="0">
	<BR>
	<INPUT type="hidden" name="root" value="{{root | safe}}"/>
	<INPUT type="hidden" name="case_id" value="{{case_id | safe}}"/>
	<INPUT type="submit" value="Add criterium">
	</FORM>

The transition to the dialogue basically just renders it:

            @endpoint("/add_criterium_dialogue", ["GET"])
            def add_criterium_dialogue_transition(self, root, case_id):
	        """
	        Endpoint which shows the dialogue for adding criteria.
	        """
	        return self.go_to_state(self.add_criterium_dialogue, this_process = request.url_root, root = root, case_id = case_id)

Finally, the endpoint for actually adding the new criterium looks like this:

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

It requests the current set of criteria from the case database in the root service, using the following auxiliary function:

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

## Change criterium dialogue transitions

The dialogue for changing a criterium is quite similar to the one for creating it. 
A difference is that the current values are filled into the name and weight fields.
Also, a delete button is included, to remove the criterion altogether.
For the database interaction, the criterion is not just added, but the previous values
are instead replaced.

The HTML code for the dialogue is in `templates\change_criterium_dialogue`:

	<H2>Change criterium</H2>
	
	<FORM action="{{this_process | safe}}change_criterium" method="post">
	<SELECT name="criterium">
	{% for c in criteria %}
	{{ c | safe }}
	{% endfor %}
	</SELECT>
	
	New name: 
	<BR>
	<INPUT type="text" name="new_name">
	<BR>
	Weight:
	<BR>
	<INPUT type="number" name="new_weight" value="" min="0">
	<BR>
	<INPUT type="hidden" name="root" value="{{root | safe}}"/>
	<INPUT type="hidden" name="case_id" value="{{case_id | safe}}"/>
	<INPUT type="submit" name="button" value="Change criterium">
	<INPUT type="submit" name="button" value="Delete criterium">
	</FORM>

It is rendered using the following endpoint:

            @endpoint("/change_criterium_dialogue", ["GET"])
            def change_criterium_dialogue_transition(self, root, case_id):
	        """
	        Endpoint which shows the dialogue for changing criteria.
	        """
	        criteria = self.get_criteria(root, case_id).keys()
	        options = ["<OPTION value=\"%s\"> %s </A>" % (c, c) for c in criteria]
	        
	        return self.go_to_state(self.change_criterium_dialogue, this_process = request.url_root, root = root, case_id = case_id, criteria = options)

The endpoint for actually changing the criterium is:

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

## Matrix dialogue and transitions

The matrix dialogue shows the Pugh table, with controls for changing the ranking of each alternative, and a save button to save those changes.
The file `templates/matrix_dialogue` should contain:

	<TD>Criterium</TD>
	<TD>Weight</TD>
	{% for a in alternatives %}
	<TD> {{ a | safe }} </TD>
	{% endfor %}
	</TR>
	
	{% for c in criteria %}
	<TR>
	<TD>
	{{ c | safe }}
	</TD>
	<TD>
	{{ weights[c] | safe }}
	</TD>
	
	{% for a in alternative_ids %}
	<TD> 
	<INPUT type="number" name="{{ a | safe }}:{{ c | safe }}" min="-1" max="1" value="{{ ranking[a][c] | safe }}">
	</TD>
	{% endfor %}
	
	</TR>
	{% endfor %}
	
	<TR>
	<TD>
	Sum
	</TD>
	<TD></TD>
	{% for s in sums %}
	<TD> 
	{{ s | safe }} 
	</TD>
	{% endfor %}

</TABLE>

<INPUT type="hidden" name="root" value="{{root | safe}}"/>
<INPUT type="hidden" name="case_id" value="{{case_id | safe}}"/>
<INPUT type="submit" value="Save">
</FORM>

The dialogue is rendered by the following endpoint:

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
	        return self.go_to_state(self.matrix_dialogue, this_process = request.url_root, root = root, case_id = case_id,
	                                alternatives = alternatives, alternative_ids = alternative_ids, 
	                                criteria = criteria, weights = weights, ranking = ranking, sums = sums)

As can be seen, this dialogue interacts quite heavily with the database, since the matrix shows all the criteria with weights, 
and all the alternatives with their ranking.

When the user presses the save button, the following endpoint is called:

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


# Porting the service to the development server

The rudimentary Pugh analysis service is now complete, and has been tested locally. To run it on a server, you just need to port all the changes to the
server environment and restart the Apache server.

