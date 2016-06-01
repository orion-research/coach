'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''

import hashlib
import json
import random
# import smtplib
import string


class Authentication:
    """
    The Authentication class provides storage for the information about users (user id, name, password hash, etc.)
    This information is stored in a json file, containing a dictionary with user name as key and the other information as a value dictionary. 
    Also, it provides functionality for generating and handling tokens. Token related information is not stored persistently. 
    """

    def __init__(self, users_filename):
        """
        Initializes the user database from file, if the file exists, or otherwise creates an empty file.
        """
        self.users_filename = users_filename
        try:
            # Read users from the file name
            with open(self.users_filename, "r") as file:
                data = file.read()
                self.users = json.loads(data)
        except:
            # File of services does not exist, so create it an empty dictionary and save it to the file
            self.users = dict()
            data = json.dumps(self.users)
            with open(self.users_filename, "w") as file:
                file.write(data)


    def user_exists(self, userid):
        """
        Returns True if the user with the given id already exists, and False otherwise.
        """
        return userid in self.users
    

    def create_user(self, userid, password, email, name):
        """
        Adds a user with the given id to the database. The password is stored as a hashed value.
        If the userid already exists in the database, that information is overwritten.
        """ 
        self.users[userid] = {"password_hash": self.password_hash(password), "email": email, "name": name}
        with open(self.users_filename, "w") as file:
            json.dump(self.users, file)

        """
        TODO: Add this functionality
        
        # Send an email to the user.
        # TODO: Remove the gmail info, put it into the settings file.
        # TODO: Create a link to an endpoint where the user can validate the password.
        gmail_address = "noreply.orionresearch@gmail.com"
        gmail_password = "<password deleted>"
        token = self.get_random_token(20)

        message_text = "To validate your COACH user identity, please follow this link: blablabla.com/" + token

        message = "\From: %s\nTo: %s\nSubject: %s\n\n%s" % (gmail_address, email, "Your COACH account", message_text)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, email, message)
            server.close()
            self.ms.logger.info("Successfully sent mail to " + email)
        except Exception as e:
            self.ms.logger.error("Failed to send mail to " + email)
            self.ms.logger.error("Exception: " + str(e))
        """
        return None
    

    def password_hash(self, password):
        """
        Returns the salted hash value for the given password.
        See https://wiki.python.org/moin/Md5Passwords.
        """
        salt = "fe5x19"
        return hashlib.md5((salt + password).encode("UTF-8")).hexdigest()
        
    
    def check_user_password(self, userid, password):
        """
        Returns True if the hash of the given password matches the one stored in the database, and otherwise False.
        """
        if userid in self.users:
            return self.users[userid]["password_hash"] == self.password_hash(password)
        else:
            return False 
    
    
    def get_user_email(self, userid):
        """
        Returns the email of a user.
        """
        return self.users[userid]["email"]
    
    
    def get_user_name(self, userid):
        """
        Returns the name of a user.
        """
        return self.users[userid]["name"]


    def get_random_token(self, length):
        """
        Generates a random token, i.e. a string of alphanumeric characters, of the requested length.
        """
        return "".join([random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) 
                        for _ in range(0, length)])


