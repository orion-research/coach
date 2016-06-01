# COACH Installation

# Dependencies
You will need to install the following software to be able to execute COACH:
- Neo4j database (community edition, version 3.x)
- Python 3.x programming language
- Python libraries: flask, requests, neo4j-driver, and virtualenv (not needed for local development)
- Apache web server (for development/production on server, not needed for local development)


# Local development
These instructions assume you will be running COACH on your local PC. It is convenient to use Eclipse as an IDE, but not a requirement.

## Neo4j
Neo4j Community Edition needs to be installed on your local machine, and be started.
Instructions are available here: http://neo4j.com/download/. Use version 3.x.

## Source code
To execute or develop COACH, you need to get the source code.

First, create the directory where you want to install the source code.
Then, use the following git commands:

	$ git init
	$ git pull https://github.com/orion-research/coach.git

## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager, do the following:

	$ pip install flask
	$ pip install requests
	$ pip install neo4j-driver=1.0.0

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
These instructions assume you will be running COACH on a Linux server. In this configuration, an Apache server is used to handle requests, instead of the server provided 
by the Flask library.

## Neo4j 
To get Neo4j, use the instructions at: http://debian.neo4j.org/ 
(under the headings "Using the Debian repository", and "Installing Neo4j". Use version 3.x.
Note that neo4j assumes that Java 8 is installed, which is not a default package for certain versions of Ubuntu and Debian Linux.)

Neo4j should now be running. To check, type:

	$ service neo4j-service status

(In some versions, the service might be called neo4j instead of neo4j-service.)

The directory /etc/neo4j/ contains various property files to change settings. 
The directory /var/lib/neo4j/data contains the actual data.

The password can be changed using curl (do sudo apt-get curl if it is not already installed):

	$ curl -H "Content-Type: application/json" -X POST -d '{"password":"WHATEVER THE PASSWORD IS"}' -u neo4j:neo4j http://localhost:7474/user/neo4j/password

(For more information ,see http://www.delimited.io/blog/2014/1/15/getting-started-with-neo4j-on-ubuntu-server.)

## Apache
Apache is installed and started as follows: 

	$ sudo apt-get update
	$ sudo apt-get install apache2
	$ sudo /etc/init.d/apache2 start

During development, it is often necessary to restart Apache when changes have been made:

	$ sudo service apache2 restart

If something goes wrong, the Apache log is the first place to look for troubleshooting:

	$ sudo cat /var/log/apache2/error.log

## Python virtual environment
To make it easier to control which Python version, and what library versions, are used, Python provides a virtual environment mechanism.
The following command installs this mechanism:

	$ sudo pip install virtualenv

(In some installations, you have to use pip3 instead of pip in all python module handling commands.)

The COACH software will be installed in the /var/www directory, and that is where the virtual environment will also reside.
	$ cd /var/www
	$ sudo mkdir COACH
	$ sudo virtualenv developmentenv

The python command in developmentenv should point at Python version 3.x, and this can be checked using:
	$ developmentenv/bin/python --version

To step into the developmentenv, use:
	$ source developmentenv/bin/activate

All changes you make are now to this local environment. To later exit the local environment, use:
	$ deactivate


## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager (sudo apt-get python3-pip), do the following inside the local environment:
	$ source developmentenv/bin/activate
	$ sudo pip install flask
	$ sudo pip install requests
	$ pip install neo4j-driver==1.0.0


## COACH source code
To execute or develop COACH, you need to get the source code.

Move to the COACH directory created before:
	$ cd /var/www/COACH

Then, use the following git commands:
	$ sudo git init
	$ sudo git pull https://github.com/orion-research/coach.git


## Configuration settings
Depending on where COACH is installed, some settings files need to update with correct url paths.
This includes the files COACH/framework/settings/root_settings_development.json, where the url path to directory must be updated,
and similarily in COACH/framework/settings/directory_settings_development.json.

The file COACH/framework/settings/directory.json, where the directory information is stored, needs to be created.
It should contain url paths to the different installed services, using this format:

	[["decision_process", "Description of decision process", "url.to.decision.process"], 
	 ["estimation_method", "Description of estimation method", "url.to.estimation.method"], ...]

Similarly, the settings files for the different decision processes in COACH/decision_processes and the estimation methods in COACH/estimation_methods need
to be updated.


## Secret data
In order for COACH to access the database, and also to encrypt some data, a file needs to be created that stores this information. Since this data is secret, it is not on GitHub,
but needs to be created. The file should be placed in the COACH/framework/settings directory, and be named root_secret_data.json. The contents of the file should look like this:

	{
		"neo4j_user_name": "your_neo4j_user_name",
        	"neo4j_password": "your_neo4j_password",
		"secret_key": "whatever string of random characters you would like to use for encryption"
	}


## Providing COACH through Apache

To be able to use Python 3 scripts with Apache, the following module needs to be added:

	$ sudo apt-get install libapache2-mod-wsgi-py3
	$ sudo service apache2 restart

The configuration information for COACH must be made available to Apache:

	$ sudo ln -s /var/www/COACH/COACH/coach-development.conf /etc/apache2/sites-available/coach-development.conf

(Depending on what services you host on the machine, this file may need to be edited.)

The Apache configuration file must be extended to give access to the directories where COACH is installed:

	$ sudo nano /etc/apache2/apache2.conf

In the editor, add the following lines:

	<Directory /var/www/COACH/COACH/>
        	Options Indexes FollowSymLinks
	        AllowOverride None
        	Require all granted
	</Directory>

Also, you need to change the permissions of the COACH files to allow Apache to execute them:

	$ sudo chmod -R 755 /var/www/COACH

Now enable the site so that Apache can find it, and restart:

	$ sudo a2ensite coach-development
	$ sudo service apache2 restart

COACH should now be up and running.


# Production server
To be defined. Will be similar to development server.