# Tutorial for creating new decision process services

This tutorial will explain how to create a new decision process service.
The tutorial will be using the Pugh analysis service as an example.
It assumes that you have installed COACH locally according to the installation instructions.

# Setting up the structure

The first step is to create the directory where the source code of the new service will be stored.
On the COACH repository, the directory COACH/decision_process contains a sub folder for each 
decision process service, so it is recommended to create a new folder there for your new process.
In the example, this folder is called PughService. (If you are using Eclipse, you can just left-click
the package decision_process, and then select New > PyDev package, after which you will be prompted 
for the package name.)

To make Python understand that this folder should be considered a Python package, you need
to create an empty file in the new folder called `__init__.py`. (If you used Eclipse when creating
the folder, this file is created automatically for you.)

In the folder, create a Python file with the name of the service, in this case PughService.py.
(In Eclipse, you can do this by left-clicking the PughService folder, and then select 
New > PyDev module. After that, you will be prompted for the module name, which is PughService, 
and also to choose a template, in which case you can select the Class template.)

In the same folder, also create a directory called templates. This will contain the html templates
that are used to generate the user interface of the service.


# Creating the initial class

Decision processes are subclasses of the generic class coach.DecisionProcessService from the 
COACH framework. To create a subclass of this, it is necessary to import the framework,
and this in turn requires that the Python import path is set up properly. To achieve this,
add the following lines in the beginning of your PughService.py file:

	# Set python import path to include COACH top directory
	import os
	import sys
	sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

	# Coach framework
	from COACH.framework import coach

Now you can create a first version of your class by adding the following lines:

	class PughService(coach.DecisionProcessService):
	
	    def process_menu(self):
	        return "Hello, Pugh!"

It is not necessary to have an `__init__` method of this class, since the superclass provides that.
(If you used Eclipse to create the file, you should delete the `__init__` method created by
the template.)

The only method that is required in a DecisionProcessService subclass is process_menu,
and you can create a temporary dummy for that by changing

It can be convenient to be able to run your service as a stand alone program. If you want to 
be able to do that, add the following line at the bottom of your file:

	if __name__ == '__main__':
    	    PughService(sys.argv[1]).run()

Now you have all you need to actually execute the service. However, you also need to provide 
some settings for the service, and these should be located in the file
local_settings.json in the COACH top directory. Add the following lines somewhere in the file:

	"PughService":
	{
		"description": "Settings for the Pugh decision process",
		"name": "Pugh analysis",
		"port": 5007,
		"logfile": "Pugh.log"
	},

The value after "port" can be any valid http port number, as long as it is not already used
by some other service. Typically, one would pick the next number after the once already listed
for other services in the file. (Note that it is possible to add more fields to this file,
so if your decision process contains other settings this is the place to put them.)

It is now possible to run the service stand-alone. Run PughService as a Python script,
and supply the path to the local_settings.json file as a command line argument. This should
result in a message similar to this:

	 * Running on http://127.0.0.1:5007/ (Press CTRL+C to quit)

Now, start your browser and point it to the adddress http://127.0.0.1:5007/process_menu,
and you should see "Hello, Pugh!" on your screen.

# Connecting the decision method to COACH for local development

The next step is to link the decision method to the COACH framework, and as a first step,
this should be done for the local development environment.

For local development, it is convenient to have a way of starting all services at once,
and this is handled by the script launch_local.py in the COACH top folder. To make it aware
of your service, you need to add the following line to that file among the import statements:

	from COACH.decision_process.PughService import PughService

Then add the following lines in the main method, among the other decision process services:

	    wdir = os.path.join(topdir, os.path.normpath("decision_process/PughService"))
	    os.chdir(wdir)
	    PughService.PughService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
	                            working_directory = wdir).run()

Finally, you need to add the new service to the directory, by editing the file directory.json
in the directory COACH/framework/settings to include the following line:

	["decision_process", "Pugh analysis", "127.0.0.1:5007"],

Here, the port number in the IP address should be the same as the one used in the local_settings
file.

You can now start COACH by first starting Neo4j and the running launch_local.py.
Use your browser to open 127.0.0.1:5000, then log in to COACH, open or create a decision case,
and select "Change decision process". In the menu you get, your new service should appear.
Select it, an then press "Select", and the line "Hello, Pugh!" should appear at the bottom left
of the screen.

You are now ready to start developing the logic of your decision process.

# How COACH decision process services work

The interactions in COACH can best be visualized through a state machine. A state in that machine
is represented by a particular screen dialogue. Therefore, typically, there is a HTML
template file associated with each state, which is complemented by adding data dynamically
from the case database.

Transitions are triggered by user interactions, such as clicking a link or pressing a button,
either in the process menu or in the dialogue. 
These interactions are sent to the service by invoking a URL, and these URLs are captured 
using something called endpoints. The endpoints are implemented as Python functions, and they 
are declared as endpoints in a method called create_endpoints, which is called by the superclass
during class initialization.

So the steps you need to take when implementing your decision process are:
1. Design the state machine and transitions.
2. For each state, create an HTML template showing the dialogue.
3. For each transition, write a Python function and declare it as an endpoint in the 
create_endpoints method.

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
alternatives is part of the generic COACH framework, and does not have to be dealt with here. (We will not deal with the
possibility of changing the baseline as part of this tutorial.) 
* The main state displays the matrix, and is the view that will be shown throughout 
most of the decision process.
* To add new criterium, a dialogue is needed.
* Also, to change the name or weight or a criterium, or remove it, another dialogue is needed.

The transitions are:
* An initial transition to the select baseline state. This is triggered from the process
menu.
* A transition from the select baseline state to the matrix dialogue state, with the side
effect of saving the selected baseline to the case database. This is triggered by a button
in the dialogue.
* A transition from the matrix dialogue state to the add criterium state. This is triggered
from the process menu.
* A transition from the add criterium state back to the matrix dialogue state, with the side
effect of adding the criterium to the case database. This is triggered by a button in the 
dialogue.
* A transition from the matrix dialogue state to the change criterium state. This is triggered
from the process menu.
* A transition from the change criterium state back to the matrix dialogue state, with the side
effect of changing or removing the criterium to the case database. This is triggered by
a button in the dialogue.
* A transition from the matrix dialogue state to itself, with the side effect of changing
the rating in a cell in the matrix. This is triggered by a Javascript function embedded in the
dialogue, which in turn is triggered when the user makes a choice in the dropdown menu
in the cell.

## State machine implementation

The web server implementation relies on the Flask framework, so certain functions need to
be imported from this library:

	# Web server framework
	from flask import request
	from flask.templating import render_template
	
	import requests


The following code sets up the state machine:

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
        
	        # Endpoints for transitions between states with side effects
	        self.ms.add_url_rule("/select_baseline", view_func = self.select_baseline, methods = ["POST"])
	        self.ms.add_url_rule("/add_criterium", view_func = self.add_criterium, methods = ["POST"])
	        self.ms.add_url_rule("/change_criterium", view_func = self.change_criterium, methods = ["POST"])
	        self.ms.add_url_rule("/change_rating", view_func = self.change_rating, methods = ["POST"])
        
The create_endpoint method overrides the one in the super class, so first we need to call it
in the superclass, to make sure that some default endpoints are set up.

In the next block, the states are defined, each state being associated with a HTML template,
which must also be created in the templates folder.

The second block is used for opening new dialogues, and the third for executing transitions
with side effects. The view_func argument indicates which method of the class will be triggered
by the end point, and all these methods need to be added to the class. Note that it is not
explicit here what states the transisions connect, but the new state will be set at the 
end of the triggered method.

For the time being, we just add stubs for the triggering methods:

	    def select_baseline_dialogue_transition(self):
	        return "Not yet implemented!"
	    
	    def add_criterium_dialogue_transition(self):
	        return "Not yet implemented!"
	    
	    def change_criterium_dialogue_transition(self):
	        return "Not yet implemented!"
	    
	    def select_baseline(self):
	        return "Not yet implemented!"
	    
	    def add_criterium(self):
	        return "Not yet implemented!"
	    
	    def change_criterium(self):
	        return "Not yet implemented!"
	    
	    def change_rating(self):
	        return "Not yet implemented!"

## Process menu

We will now also put the process menu in place. It requires an update of the process_menu method:

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

The HTML template for the process menu will look like follows: 

	<LI><A HREF="/main_menu?main_dialogue={{url}}select_baseline_dialogue?case_id={{ case_id | safe }}">Select baseline</A></LI>
	<LI><A HREF="/main_menu?main_dialogue={{url}}add_criterium_dialogue?case_id={{ case_id | safe }}">Add criterium</A></LI>
	<LI><A HREF="/main_menu?main_dialogue={{url}}change_criterium_dialogue?case_id={{ case_id | safe }}">Change criterium</A></LI>

Each line is a list item representing a menu choice, that just triggers the corresponding
endpoints. The double curly braces `{{ ... }}` are used to insert the parameters that were 
supplied to the rendering function. (For more details on the template syntax,
look up documentation on the Jinja2 template engine, which is used by the Flask
web framework that COACH employs.)

You can now restart the COACH local implementation, and check that the process menu works.

## Select baseline dialogue and transitions

To implement the selection of a baseline, a HTML template for the dialogue is needed:

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

The decision alternatives to choose from are stored in the case database, which is held by
the root service. Therefore, a request for this data has to be made in order to build
the list of alternatives.

Since the alternatives are provided from the root service as a json string, the json library
needs to be imported:

	import json

When the user has chosen a baseline in the menu, and presses the select button, the
select_baseline endpoint gets invoked. Its method is as follows:

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
	        return self.matrix_dialogue_transition(this_process = request.url_root, root = root, case_id = case_id)

It writes the id of the selected alternative to the case database as a property of the case node.
It then displays the Pugh matrix dialogue.

Since the matrix dialogue will build the matrix from the database, we will provide a helper
function for the transition to that dialogue, which initially just looks like this:

	    def matrix_dialogue_transition(self, this_process, root, case_id):
	        return self.redirect_to_state(self.matrix_dialogue, this_process = request.url_root, root = root, case_id = case_id)


TODO: EXPLAIN DIFFERENCE BETWEEN go_to_state AND redirect_to_state, AND WHEN TO USE WHICH.


## Add criterium dialogue and transitions

The add criterium dialogue is fairly similar to the select baseline, except that it contains
a text field for the name of the criterion, and a numerical field for its weight:

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

	    def add_criterium_dialogue_transition(self):
	        root = request.values["root"]
	        case_id = request.values["case_id"]
	        return self.go_to_state(self.add_criterium_dialogue, this_process = request.url_root, root = root, case_id = case_id)

Finally, the endpoint for actually adding the new criterium looks like this:

	    def add_criterium(self):
	        root = request.values["root"]
	        case_id = request.values["case_id"]
	        criterium = request.values["criterium"]
        
	        # TODO: How to store weight??
	        weight = request.values["weight"]
	
	        # Get the current set of criteria from the case database, and add the new one to the set
	        criteria = requests.get(root + "get_case_property", params = {"case_id": case_id, "name": "criteria"}).text
	        if criteria:
	            # Json does not allow '...' as string delimiters, so they must be changed to "..." 
	            criteria = json.loads(criteria.replace("'", "\"")) + [criterium]
	        else:
	            criteria = [criterium]
	        
	        # Write the updated set to the database
	        requests.post(root + "change_case_property", data = {"case_id": str(case_id), "name": "criteria", "value": str(criteria)})
	
	        # Go to the matrix dialogue state
	        return self.matrix_dialogue_transition(this_process = request.url_root, root = root, case_id = case_id)

It requests the current set of criteria from the case database in the root service.
If there were any already defined, the new one is added to the end of the list.
Otherwise, the the criterium is added as the first one.
Finally, the matrix dialogue is shown again, now with an extra row for the new criterium.

TODO: UPDATE THIS FUNCTION TO ALSO STORE THE WEIGHT OF THE CRITERIUM.

## Change criterium dialogue transitions

The dialogue for changing a criterium is quite similar to the one for creating it. 
A difference is that the current values are filled into the name and weight fields.
Also, a delete button is included, to remove the criterion altogether.
For the database interaction, the criterion is not just added, but the previous values
are instead replaced.

TODO: ADD THE CODE FOR THIS.

## Matrix dialogue and transitions

TODO: ADD THIS.

# Porting the service to the development server
To be added. The files that need updating are:
- pugh.wsgi
- development_settings.json
- coach-development.conf
- directory.json

