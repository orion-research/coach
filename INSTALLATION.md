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

# For developers
These instructions assume you will be running COACH on your local PC.

To be written...

# For production
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

## Configuration settings
Depending on where COACH is installed, some settings files need to update with correct paths.
This includes the files COACH/framework/settings/root_settings.json, where the path to directory must be updated,
and COACH/framework/settings/directory.json, where the directory information is stored, with paths to the
different installed services.

Examples of the format of these files can be found in the same directory, as example_root_settings.json
and example_directory.json.

## Running COACH

To start running the services, move to the directory where you installed the source code from GitHub. Then run the bash script as follows:

$ ./launch.sh <neo4j user name> <neo4j password> <session secret key, which is any random string>

This should start a number of python3 processes, one for each service. To later stop all those processes (assuming you have not started any other python3 processes that you want to keep), type:

$ pkill python3
