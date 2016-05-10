# COACH Installation

# Source code
To execute or develop COACH, you need to get the source code.

First, create the directory where you want to install the source code.
Then, use the following git commands:

$ git init

$ git pull https://github.com/orion-research/coach.git

# Dependencies
You will need to install the following software to be able to execute COACH:
- Neo4j database (community edition)
- Python 3 programming language
- Python libraries: flask, requests, neo4jrestclient

# Local development
These instructions assume you will be running COACH on your local PC. It is convenient to use Eclipse as an IDE, but not a requirement.

## Neo4j
Neo4j Community Edition needs to be installed on your local machine, and be started.
Instructions are available here: http://neo4j.com/download/.

## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager, do the following:

$ pip install flask

$ pip install requests

$ pip install neo4jrestclient

(In some installations, you have to use pip3 instead of pip in the above commands.)

## Secret data
In order for COACH to access the database, and also to encrypt some data, a file needs to be created that stores this information. Since this data is secret, it is not on GitHub,
but needs to be created. The file should be placed in the COACH/framework/settings directory, and be named root_secret_data.json. The contents of the file should look like this:

	{
		"neo4j_user_name": "your_neo4j_user_name",
        	"neo4j_password": "your_neo4j_password",
		"secret_key": "whatever string of random characters you would like to use for encryption"
	}

## Running COACH
To start all the services, a small Python script has been created in the COACH folder, that starts all the services. It can be ran from inside Eclipse, or from the command line:

$ python launch-local.py <neo4j user name> <neo4j password> <random string>

(In some installations, you have to use python3 instead of python in the above command.)

In the above command, <neo4j user name> and <neo4j password> should be replaced by whatever username and password you have selected for the database.
The <random string> parameter is used for encrypting the user passwords in the authentication module. It can be any string, but what is important is that
the same string is used on all invocations.

To start interacting with COACH, open http://127.0.0.1:5000 in a web browser.


# Development server
These instructions assume you will be running COACH on a Linux server.

## Neo4j 
To get Neo4j, use the instructions at: http://debian.neo4j.org/ 
(under the headings "Using the Debian repository", and "Installing Neo4j")

Neo4j should now be running. To check, type:

$ service neo4j-service status

The directory /etc/neo4j/ contains various property files to change settings. 
The directory /var/lib/neo4j/data contains the actual data.

The password can be changed using curl (do sudo apt-get curl if it is not already installed):
curl -H "Content-Type: application/json" -X POST -d '{"password":"WHATEVER THE PASSWORD IS"}' -u neo4j:neo4j http://localhost:7474/user/neo4j/password

(For more information ,see http://www.delimited.io/blog/2014/1/15/getting-started-with-neo4j-on-ubuntu-server.)

## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager, do the following:

$ sudo pip install flask

$ sudo pip install requests

$ sudo pip install neo4jrestclient

(In some installations, you have to use pip3 instead of pip in the above commands.)

## Configuration settings
Depending on where COACH is installed, some settings files need to update with correct url paths.
This includes the files COACH/framework/settings/root_settings_development.json, where the url path to directory must be updated,
and COACH/framework/settings/directory_development.json, where the directory information is stored, with url paths to the
different installed services.

## Secret data
In order for COACH to access the database, and also to encrypt some data, a file needs to be created that stores this information. Since this data is secret, it is not on GitHub,
but needs to be created. The file should be placed in the COACH/framework/settings directory, and be named root_secret_data.json. The contents of the file should look like this:

	{
		"neo4j_user_name": "your_neo4j_user_name",
        	"neo4j_password": "your_neo4j_password",
		"secret_key": "whatever string of random characters you would like to use for encryption"
	}

## Running COACH

To start running the services, move to the directory where you installed the source code from GitHub. Then run the following command:

$ python launch-development.py <neo4j user name> <neo4j password> <random string> &

To later stop, type:

$ pkill python3


# Production server
To be defined.