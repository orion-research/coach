# COACH Installation

# Dependencies
You will need to install the following software to be able to execute COACH:
- Neo4j database (community edition, version 3.x)
- Python 3.x programming language
- Python package manager (pip) and some libraries
- Apache web server (for development/production on server, not needed for local development)


# Local development
These instructions assume you will be running COACH on your local PC.
It is convenient to use an IDE for Python, such as PyCharm or Eclipse with the PyDev extension, but it is not a requirement.
It is also convenient to use source code analysis tools to improve quality, such as
PyLint (see https://codeyarns.com/2015/01/02/how-to-use-pylint-for-eclipse/ on how to combine this with Eclipse).

## Neo4j
Neo4j Community Edition needs to be installed on your local machine, and be started.
Instructions are available here: http://neo4j.com/download/. Use version 3.x.

## Source code
To execute or develop COACH, you need to get the source code, which assumes that you have Git installed.

First, create the directory where you want to install the source code.
Then, use the following git commands:

	$ git init
	$ git pull https://github.com/orion-research/coach.git

## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager, do the following:

	$ pip install flask
	$ pip install requests
	$ pip install neo4j-driver==1.0.0
	$ pip install rdflib
	$ pip install sqlalchemy
	$ pip install rdflib-sqlalchemy

(In some installations, you have to use pip3 instead of pip in the above commands.)

## Configuration settings

Most of the settings used by the system are stored in one file in the COACH top directory. However, since the installation can be done
in different ways, the repository contains several alternative setting files, and depending on how the system is deployed the correct
one must be indicated. This is done by creating a symbolic file link from "settings.json" in the COACH top directory to the appropriate
settings file. On a Linux system the command for a local installation is (assuming you are in the right directory):

	$ sudo ln -s local_settings.json settings.json

On a Windows system, the corresponding command is:

	$ mklink settings.json local_settings.json 

Note that you need full elevated rights to run this command on a Windows system. Run cmd.exe as an Administrator by pressing and holding Ctrl+Shift while opening the program.

## Secret data
In order for COACH to access the database, and also to encrypt some data, a file needs to be created that stores this information. Since this data is secret, it is not on GitHub,
but needs to be created locally for each installation. The file should be placed in the COACH/framework/settings directory, and be named root_secret_data.json. The contents of the file should look like this:

	{
		"neo4j_user_name": "your_neo4j_user_name",
        	"neo4j_password": "your_neo4j_password",
		"secret_key": "whatever string of random characters you would like to use for encryption",
		"email_password": "the password for the email account used for sending email from COACH",
		"github_key": "another string of random characters, only needed in case you plan to use GitHub webhooks",
	        "password_hash_salt" : "a shorter random string"
	}

## Running COACH
To run COACH, you first need to start neo4j. Then, to start all the services, a small Python script has been created in the COACH folder. It can be ran from inside Eclipse, or from the command line:

	$ python launch_local.py

(In some installations, you have to use python3 instead of python in the above command.)

To start interacting with COACH, open http://127.0.0.1:5000 in a web browser.

## Running tests
To run tests, you first need to install some more libraries

    $ pip install selenium

Then, selenium needs a driver that must be in the path (for example, /usr/bin or /usr/local/bin). You can download it at the address https://github.com/mozilla/geckodriver/releases
See http://selenium-python.readthedocs.io/installation.html for more information.

Once this is done, you can run the tests by going to the test directory
    $ cd COACH/test/test_global

Then, you can run all tests at once
    $ python TestGlobal.py
Or only one at a time, e.g.
    $ python TestSimilarity.py

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

You may need to be the owner of this directory for some commands to work properly, so change the ownership:

	$ sudo chown -R <your user id> /var/www/developmentenv

## Python libraries
Having installed Python 3.x (whatever the latest version is), and the pip package manager (sudo apt-get python3-pip), do the following inside the local environment:

	$ source developmentenv/bin/activate
	$ sudo pip install flask
	$ sudo pip install requests
	$ sudo pip install neo4j-driver==1.0.0
	$ sudo pip install rdflib
	$ sudo pip install sqlalchemy
	$ sudo pip install rdflib-sqlalchemy


## COACH source code
To execute or develop COACH, you need to get the source code.

Move to the COACH directory created before:

	$ cd /var/www/COACH

Then, use the following git commands:

	$ sudo git init
	$ sudo git pull https://github.com/orion-research/coach.git


The system needs to be able to create a file for the database, which requires changing file permissions for the corresponding directory:

	$ sudo chmod 777 /var/www/COACH/COACH/framework/settings
	

## Configuration settings
Depending on where and how COACH is installed, the settings in the file COACH/development_settings.json need to be updated.

Most of the settings used by the system are stored in one file in the COACH top directory. However, since the installation can be done
in different ways, the repository contains several alternative setting files, and depending on how the system is deployed the correct
one must be indicated. This is done by creating a symbolic file link from "settings.json" in the COACH top directory to the appropriate
settings file. On a Linux system the command for a local installation is (assuming you are in the right directory):

	$ sudo ln -s local_settings.json settings.json

The file COACH/framework/settings/directory.json, where the directory information is stored, needs to be created.
It should contain url paths to the different installed services, using this format:

	[["decision_process", "Description of decision process", "url.to.decision.process"], 
	 ["estimation_method", "Description of estimation method", "url.to.estimation.method"], ...]


## Secret data
In order for COACH to access the database, and also to encrypt some data, a file needs to be created that stores this information. Since this data is secret, it is not on GitHub,
but needs to be created. The file should be placed in the COACH/framework/settings directory, and be named root_secret_data.json. The contents of the file should look like this:

	{
		"neo4j_user_name": "your_neo4j_user_name",
		"neo4j_password": "your_neo4j_password",
		"secret_key": "whatever string of random characters you would like to use for encryption"
	}


## Providing COACH through Apache

To be able to use Python 3 scripts with Apache, the mod_wsgi module needs to be added. It is important to use version 4.2+ of this module together with Python 3.4+.

	$ sudo apt-get install apache2-dev
	$ source developmentenv/bin/activate
	$ pip install mod_wsgi
	$ deactivate

Now, Apache needs to be informed about this new module:

	$ sudo developmentenv/bin/mod_wsgi-express install-module

Edit the following file:

	$ sudo nano /etc/apache2/mods-available/wsgi_express.load 

In the file, enter the following text, and then save the file (ctrl-X):

	LoadModule wsgi_module /usr/lib/apache2/modules/mod_wsgi-py34.cpython-34m.so

Also edit the following file:

	$ sudo nano /etc/apache2/mods-available/wsgi_express.conf

In the file, enter the following text, and then save the file (ctrl-X):

	WSGIPythonHome /var/www/developmentenv

Enable the module, and restart Apache:

	$ sudo a2enmod wsgi_express
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


## Configuring https

To ensure basic security, COACH should be set up to use certificates and encryption through https. As a first step,
Apache is configured to use encryption:

	$ sudo a2enmod ssl
	$ sudo a2ensite default-ssl.conf
	$ sudo service apache restart

Certificates can be obtained using the free letsencrypt service. The following steps are needed to install the service:

	$ sudo apt-get update
	$ sudo git clone https://github.com/letsencrypt/letsencrypt /opt/letsencrypt

To set up certificates, do the following (replacing example.com with your domain name):

	$ cd /opt/letsencrypt
	$ ./letsencrypt-auto --apache -d example.com
	$ ./letsencrypt-auto --apache -d example.com -d www.example.com

The last step starts (after a while) an interactive setup process. When it has been completed, the certificates can be found in
`/etc/letsencrypt/live`, where the certificate is in `cert.pem` and the encryption key in `privkey.pem`.

The installation can be tested from a browser using the URL `https://www.ssllabs.com/ssltest/analyze.html?d=example.com&latest`.

The certificates have a limited validity, so it is advisable to automatically update them before expiration:

	$ /opt/letsencrypt/letsencrypt-auto renew
	$ sudo crontab -e

The last command opens a file in an editor. Put the following text into one line of the file, and save it:

	30 2 * * 1 /opt/letsencrypt/letsencrypt-auto renew >> /var/log/le-renew.log

This will make the system update the certificates every Monday at 2:30 AM.

Now the Apache virtual hosts must be told where to find the certificates, and also to use the SSL encryption. 
Make sure that the configuration file for any virtual host that should run https contains the following lines:

	SSLCertificateFile /etc/letsencrypt/live/cert.pem
	SSLCertificateKeyFile /etc/letsencrypt/live/privkey.pem
	SSLEngine on


Finally, restart Apache again:

 	$ sudo service apache restart


## Security hardening
Based on the output of testing in a browser the URL `https://www.ssllabs.com/ssltest/analyze.html?d=example.com&latest`, some
actions may be needed.

The SSLv3 is not considered secure any more, so some settings may need to change. Find the appropriate files using:

	$ grep -i -r "SSLProtocol" /etc/apache2

In the indicated files, change `SSLProtocol all` to `SSLProtocol all -SSLv2 -SSLv3`.

There are also issues with RC4 encryption. In the same file, the following lines should be added:

	SSLHonorCipherOrder On
	SSLCipherSuite ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:!aNULL:!MD5:!DSS


## Trouble shooting

- Apache does not give much feedback on errors in the wsgi setup. Therefore, it is advisable to test each *.wsgi file individually by 
simply running `python file.wsgi` (or python3) from the terminal. This will detect issues such as path errors etc.
If there is no output, everything should be ok.

- The Apache configuration files can be tested for syntax errors by running `apachectl -t`. The command `apachectl -S` can be used to 
produce a listing of the different virtual hosts set up, to help discovering if they are conflicting in some way.

- File permissions are important, and there is not much feedback if they are wrong.

- In some situations, it appears that Apache chooses to use its default virtual host rather than the one provided by COACH
to listen on port 80. This shows up as a default Apache page in the browser rather than the COACH login page. 
A fix to this is to copy the contents of the COACH port 80 virtual host to the default host configuration file.

- The ports used by COACH services must be open to the Internet in the firewalls to allow external access to the server. If a port is closed, one possible indication is a very long (many seconds) response time for a request, followed by a message in the browser indicating that the service was not available.

- Sometimes, it can appear that a code change did not take effect. If so, it could be the browser that caches pages from the previous version instead of showing a newly generated page. Check that the version number shown on the page corresponds to the current version of the source code, and if not, do a hard update of the page.

## Configuring GitHub webhooks

COACH is prepared for automatic updates of the server version when new commits are made to GitHub.

To activate it, log in to the GitHub account, select "Settings" and then select "Webhooks and services". Enter the following information:
- Under Payload URL, enter: https://your.coach.server.url/github_update.
- Under Secret, enter a random string, which should also be included in the secret data file.
- Under Which events..., select "Just the push event".
- Under Activate, select the checkbox.
- Press Add webhook.

You also need to update the sudoers file to not require a password, and file permissions need to be changed.
The sudoers file must be edited using sudo visudo.

# Production server
To be defined. Will be similar to development server.

