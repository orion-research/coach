'''
Created on 20 maj 2016

@author: Jakob Axelsson
'''

import email.utils
import hashlib
import json
import os
import random
import smtplib
import string

from COACH.framework.coach import Microservice, endpoint


class AuthenticationService(Microservice):
    """
    The AuthenticationService class provides storage for the information about users (user id, name, password hash, etc.)
    This information is stored in a json file, containing a dictionary with user name as key and the other information as a value dictionary. 
    Also, it provides functionality for generating and handling tokens. 
    """

    def __init__(self, settings_file_name = None, working_directory = None):
        """
        Initializes the user database from file, if the file exists, or otherwise creates an empty file.
        """
        
        super().__init__(settings_file_name, working_directory = working_directory)

        # Read secret data file
        secret_data_file_name = self.get_setting("secret_data_file_name")
        with open(os.path.join(self.working_directory, os.path.normpath(secret_data_file_name)), "r") as file:
            fileData = file.read()
        secret_data = json.loads(fileData)
        self.password_hash_salt = secret_data["password_hash_salt"]

        self.users_filename = self.get_setting("authentication_database")
        self.email_settings = self.get_setting("email")
        self.get_setting("email")["password"] = secret_data["email_password"]

        self.authentication_service_url = self.get_setting("protocol") + "://" + self.get_setting("host") + ":" + str(self.get_setting("port"))
        
        try:
            self.load_data()
        except:
            # File of services does not exist, so create it an empty dictionary and save it to the file
            self.users = dict()
            self.save_data()


    def save_data(self):
        """
        Saves the current content of the user database to file.
        """
        data = json.dumps(self.users, indent = 4)
        with open(os.path.join(self.working_directory, self.users_filename), "w") as file:
            file.write(data)
        

    def load_data(self):
        """
        Loads the currently saved content in the user database file.
        """
        with open(os.path.join(self.working_directory, self.users_filename), "r") as file:
            data = file.read()
            self.users = json.loads(data)


    def get_random_token(self, length):
        """
        Generates a random token, i.e. a string of alphanumeric characters, of the requested length.
        """
        return "".join([random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) 
                        for _ in range(0, length)])


    def confirm_user_token(self, user_id, user_token):
        """
        Returns True if the user's user token matches the provided.
        """
        return user_id in self.users and self.users[user_id]["user_token"] == user_token


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
        server.quit()

            
    def password_hash(self, password):
        """
        Returns the salted hash value for the given password.
        See https://wiki.python.org/moin/Md5Passwords.
        """
        return hashlib.md5((self.password_hash_salt + password).encode("UTF-8")).hexdigest()
        
    
    @endpoint("/user_exists", ["GET", "POST"])
    def user_exists(self, user_id):
        """
        Returns True if the user with the given id already exists and has been confirmed, and False otherwise.
        """
        return json.dumps(user_id in self.users and not "confirmation_token" in self.users[user_id])
    

    @endpoint("/create_user", ["POST"])
    def create_user(self, user_id, password, email, name):
        """
        Adds a user with the given id to the database. The password is stored as a hashed value.
        If the user_id already exists in the database, that information is overwritten.
        The user is given a random confirmation token, which must be cleared before the user can log in.
        The user is sent an email with a URL to perform this confirmation.
        """ 
        token = self.get_random_token(20)
        self.users[user_id] = {"password_hash": self.password_hash(password), "email": email, "name": name, 
                              "confirmation_token": token}
        self.save_data()
        
        message_body = "To validate your COACH user identity, please follow this link:\n\n{0}/confirm_account?user_id={1}&token={2}"
        print(message_body)
        self.send_email(email, "COACH account validation", message_body.format(self.authentication_service_url, user_id, token))
        return json.dumps(None)
    

    @endpoint("/logout_user", ["POST"])
    def logout_user(self, user_id, user_token):
        """
        Revokes the user token associated with the current user, and return "Ok".
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            self.users[user_id].pop("user_token")
            self.save_data()
            return json.dumps("Ok")
        else:
            return json.dumps(None)
        
        
    @endpoint("/confirm_account", ["GET", "POST"])
    def confirm_account(self, user_id, token):
        """
        Tries to confirm the user_id with the provided token. If this was successful, i.e. if the token matches
        the stored one (or if the account has already been confirmed), the function returns True. Otherwise,
        it returns False, in which case the account remains unconfirmed.
        """

        ok_message = "Account of " + user_id + " has been confirmed! You may now log in."
        nok_message = "Error: The token provided for validating account of " + user_id + " was not valid."
        if user_id in self.users:
            # User exists
            if "confirmation_token" in self.users[user_id]:
                # User is unconfirmed
                if self.users[user_id]["confirmation_token"] == token:
                    # Token matches, so clear it and return True
                    self.users[user_id].pop("confirmation_token")        
                    self.save_data()
                    return ok_message
                else:
                    return nok_message
            else:
                return ok_message
        else:
            return nok_message
        
        
    @endpoint("/check_user_password", ["POST"])
    def check_user_password(self, user_id, password):
        """
        Returns a random token if the hash of the given password matches the one stored in the database, 
        and otherwise returns None. The token is also stored in the user database.
        """
        if user_id in self.users and self.users[user_id]["password_hash"] == self.password_hash(password):
            user_token = self.get_random_token(20)
            self.users[user_id]["user_token"] = user_token
            self.save_data()
            return json.dumps(user_token)
        else:
            return json.dumps(None) 
    
    
    @endpoint("/get_user_email", ["GET", "POST"])
    def get_user_email(self, user_id):
        """
        Returns the email of a user.
        """
        return json.dumps(self.users[user_id]["email"])
    
    
    @endpoint("/get_user_name", ["GET", "POST"])
    def get_user_name(self, user_id):
        """
        Returns the name of a user.
        """
        return json.dumps(self.users[user_id]["name"])


    @endpoint("/get_delegate_token", ["POST"])
    def get_delegate_token(self, user_id, case_id, user_token):
        """
        Returns a new delegate token, which is also stored in the user database and associated with a certain case.
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            delegate_token = self.get_random_token(20)
            self.users[user_id]["delegate"] = { "token": delegate_token, "case": case_id }
            self.save_data()
            return json.dumps(delegate_token)
        else:
            return json.dumps(None)
        
        
    @endpoint("/revoke_delegate_token", ["POST"])
    def revoke_delegate_token(self, user_id, user_token):
        """
        Revokes the delegate token associated with the current user, and return "Ok".
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            self.users[user_id].pop("delegate")
            self.save_data()
            return json.dumps("Ok")
        else:
            return json.dumps(None)
        
        
    @endpoint("/check_user_token", ["POST"])
    def check_user_token(self, user_id, user_token):
        """
        Returns True if the current user token of user_id matches the provided.
        """
        if self.confirm_user_token(user_id, user_token):
            return json.dumps(self.users[user_id]["user_token"] == user_token)
        else:
            return json.dumps(False)
    
    
    @endpoint("/check_delegate_token", ["POST"])
    def check_delegate_token(self, user_id, case_id, delegate_token):
        """
        Returns True if the current delegate token of user_id matches the provided, and the case_id matches the one associated with the delegate.
        """
        if user_id in self.users and "delegate" in self.users[user_id]:
            return json.dumps(self.users[user_id]["delegate"]["token"] == delegate_token and 
                              self.users[user_id]["delegate"]["case"] == case_id)
        else:
            return json.dumps(False)
