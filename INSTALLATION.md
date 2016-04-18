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

$ service neo4j-service.

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

## Running COACH

To make sure that Python imports are resolved correctly, do the following:

$  PYTHONPATH="${PYTHONPATH}:path"

where path is the path to the directory where the source code from GitHub was installed.

To start running the services, move to the directory where you installed the source code from GitHub.
Then move to the directory COACH/framework, and do the following to start the root service
and a sample directory service:

$ nohup python3 launch.py <neo4j user name> <neo4j password> <session secret key, which is any random string> &

(Take note of the PID printed on the screen, in case you need to kill the process later.)

To start any other service (for decision processes, estimation methods), move to the directory where the 
source code is located and do:

$ nohup python3 service.py &

where service.py is the name of the file implementing the service.