'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''

import email.utils
import hashlib
import json
import random
import smtplib
import string


class Authentication:
    """
    The Authentication class provides storage for the information about users (user id, name, password hash, etc.)
    This information is stored in a json file, containing a dictionary with user name as key and the other information as a value dictionary. 
    Also, it provides functionality for generating and handling tokens. 
    """

    def __init__(self, users_filename, email_settings, root_service_url, password_hash_salt):
        """
        Initializes the user database from file, if the file exists, or otherwise creates an empty file.
        """
        self.users_filename = users_filename
        self.email_settings = email_settings
        self.root_service_url = root_service_url
        self.password_hash_salt = password_hash_salt
        
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
        Returns True if the user with the given id already exists and has been confirmed, and False otherwise.
        """
        return userid in self.users and not "confirmation_token" in self.users[userid]
    

    def create_user(self, userid, password, email, name):
        """
        Adds a user with the given id to the database. The password is stored as a hashed value.
        If the userid already exists in the database, that information is overwritten.
        The user is given a random confirmation token, which must be cleared before the user can log in.
        The user is sent an email with a URL to perform this confirmation.
        """ 
        token = self.get_random_token(20)
        self.users[userid] = {"password_hash": self.password_hash(password), "email": email, "name": name, 
                              "confirmation_token": token}
        with open(self.users_filename, "w") as file:
            json.dump(self.users, file)

        message_body = "To validate your COACH user identity, please follow this link:\n\n{0}/confirm_account?user={1}&token={2}"
        self.send_email(email, "COACH account validation", message_body.format(self.root_service_url, userid, token))
        return None
    

    def send_email(self, recipient, title, body):
        """
        Sends an email to the designated recipient, with title and body.
        """
        sender = self.email_settings["sender"]
        date = email.utils.formatdate()
        message_template = "From: {0}\nTo: {1}\nSubject: {2}\nDate: {3}\n\n{4}\n"
        message = message_template.format(sender, recipient, title, date, body)
        server = smtplib.SMTP(self.email_settings["server"], self.email_settings["port"])
        server.ehlo("")
        server.starttls()
        server.login(sender, self.email_settings["password"])
        server.sendmail(sender, recipient, message)
        server.close

            
    def confirm_account(self, userid, token):
        """
        Tries to confirm the userid with the provided token. If this was successful, i.e. if the token matches
        the stored one (or if the account has already been confirmed), the function returns True. Otherwise,
        it returns False, in which case the account remains unconfirmed.
        """

        if userid in self.users:
            # User exists
            if "confirmation_token" in self.users[userid]:
                # User is unconfirmed
                if self.users[userid]["confirmation_token"] == token:
                    # Token matches, so clear it and return True
                    self.users[userid].pop("confirmation_token")        
                    with open(self.users_filename, "w") as file:
                        json.dump(self.users, file)
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False
        
        
    def password_hash(self, password):
        """
        Returns the salted hash value for the given password.
        See https://wiki.python.org/moin/Md5Passwords.
        """
        return hashlib.md5((self.password_hash_salt + password).encode("UTF-8")).hexdigest()
        
    
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


