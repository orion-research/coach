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
import datetime


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
        
    
    @endpoint("/user_exists", ["GET", "POST"], "application/json")
    def user_exists(self, user_id):
        """
        Returns True if the user with the given id already exists and has been confirmed, and False otherwise.
        """
        return user_id in self.users and not "confirmation_token" in self.users[user_id]
    

    @endpoint("/create_user", ["POST"], "text/plain")
    def create_user(self, user_id, password, email, name):
        """
        Adds a user with the given id to the database. The password is stored as a hashed value.
        If the user_id already exists in the database, that information is overwritten.
        The user is given a random confirmation token, which must be cleared before the user can log in.
        The user is sent an email with a URL to perform this confirmation.
        """ 
        token = self.get_random_token(20)
        self.users[user_id] = {"password_hash": self.password_hash(password), "email": email, "name": name, 
                              "confirmation_token": token, "uri": self.authentication_service_url + "/user#" + user_id }
        self.save_data()
        
        message_body = "To validate your COACH user identity, please follow this link:\n\n{0}/confirm_account?user_id={1}&token={2}"
        print(message_body)
        self.send_email(email, "COACH account validation", message_body.format(self.authentication_service_url, user_id, token))
        return "Ok"
       
        
    @endpoint("/reset_password", ["POST"], "text/plain")
    def reset_password(self, email):
        """
        Resets the password and sends an email to the user.
        """ 
        for (user_id,user_data) in self.users.items():
             
            if user_data["email"] == email:    
                new_password = self.get_random_token(20)
                self.users[user_id]["password_hash"] = self.password_hash(new_password)
                self.save_data()
                
                message_body = "Your COACH password has been reset to: " + new_password
                print(message_body)
                self.send_email(email, "COACH password reset", message_body)
                return "Ok"
        
        return "Email not found"
        
        
    @endpoint("/change_password", ["POST"], "text/plain")
    def change_password(self, user_id, user_token):
        """
        Changes the password.
        """       
        print("¤¤¤¤¤¤¤ change_password called")
        if self.confirm_user_token(user_id, user_token):
            print("¤¤¤¤¤¤¤ Let's make a password for you!")                           
            return "Ok"
        else:
            return None
        
        
    @endpoint("/get_users", ["POST"], "application/json")
    def get_users(self):
        """
        Returns the list of all registered users, as a list of tuples (user_id, uri, email, name).
        """
        return [(user_id, self.get_user_uri(user_id), self.users[user_id]["email"], self.users[user_id]["name"]) 
                for user_id in self.users.keys()]


    @endpoint("/logout_user", ["POST"], "application/json")
    def logout_user(self, user_id, user_token):
        """
        Revokes the user token associated with the current user, and return "Ok".
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            self.users[user_id].pop("user_token")
            self.save_data()
            return "Ok"
        else:
            return None
        
        
    @endpoint("/confirm_account", ["GET", "POST"], "text/plain")
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
        
        
    @endpoint("/check_user_password", ["POST"], "application/json")
    def check_user_password(self, user_id, password):
        """
        Returns a random token if the hash of the given password matches the one stored in the database, 
        and otherwise returns None. The token is also stored in the user database, together with 
        the date and time of the login.
        """
        if user_id in self.users and self.users[user_id]["password_hash"] == self.password_hash(password):
            user_token = self.get_random_token(20)
            self.users[user_id]["user_token"] = user_token
            self.users[user_id]["login_time"] = datetime.datetime.now().isoformat()
            self.save_data()
            return user_token
        else:
            return None 

    @endpoint("/set_user_profile", ["GET", "POST"], "application/json")
    def set_user_profile(self, user_id, user_name, company_name, email):
        """
        Saves the profile of a user.
        """
        self.users[user_id]["name"] = user_name
        self.users[user_id]["company_name"] = company_name
        self.users[user_id]["email"] = email
        self.save_data()
    
        
    @endpoint("/get_user_email", ["GET", "POST"], "application/json")
    def get_user_email(self, user_id):
        """
        Returns the email of a user.
        """
        return self.users[user_id]["email"]
    
    
    @endpoint("/get_user_name", ["GET", "POST"], "application/json")
    def get_user_name(self, user_id):
        """
        Returns the name of a user.
        """
        return self.users[user_id]["name"]


    @endpoint("/get_company_name", ["GET", "POST"], "application/json")
    def get_company_name(self, user_id):
        """
        Returns the company name of a user.
        """
        return self.users[user_id]["company_name"] if "company_name" in self.users[user_id] else ""


    @endpoint("/get_user_uri", ["GET", "POST"], "application/json")
    def get_user_uri(self, user_id):
        """
        Returns the uri of a user.
        """
        return self.authentication_service_url + "/user#" + user_id
    

#    @endpoint("/get_user_uri", ["GET", "POST"], "application/json")
#    def get_user_uri(self, user_id):
#        """
#        Returns the uri of a user.
#        """
#        if user_id not in self.users.keys():
#            return None
#        elif "uri" not in self.users[user_id].keys():
#            self.users[user_id]["uri"] = self.authentication_service_url + "/user#" + user_id
#            self.save_data()
#        return self.users[user_id]["uri"]


    @endpoint("/get_user_namespace", ["GET", "POST"], "application/json")
    def get_user_namespace(self):
        """
        Returns the namespace for user uri:s.
        """
        return self.authentication_service_url + "/user#"

    
    @endpoint("/get_delegate_token", ["POST"], "application/json")
    def get_delegate_token(self, user_id, case_id, user_token):
        """
        Returns a new delegate token, which is also stored in the user database and associated with a certain case.
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            delegate_token = self.get_random_token(20)
            self.users[user_id]["delegate"] = { "token": delegate_token, "case": case_id }
            self.save_data()
            return delegate_token
        else:
            return None
        
        
    @endpoint("/revoke_delegate_token", ["POST"], "application/json")
    def revoke_delegate_token(self, user_id, user_token):
        """
        Revokes the delegate token associated with the current user, and return "Ok".
        If the user_id's user token does not match the provided, None is returned.
        """
        if self.confirm_user_token(user_id, user_token):
            self.users[user_id].pop("delegate")
            self.save_data()
            return "Ok"
        else:
            return None
        
        
    @endpoint("/check_user_token", ["POST"], "application/json")
    def check_user_token(self, user_id, user_token):
        """
        Returns True if the current user token of user_id matches the provided.
        """
        if self.confirm_user_token(user_id, user_token):
            return self.users[user_id]["user_token"] == user_token
        else:
            return False
    
    
    @endpoint("/check_delegate_token", ["POST"], "application/json")
    def check_delegate_token(self, user_id, case_id, delegate_token):
        """
        Returns True if the current delegate token of user_id matches the provided, and the case_id matches the one associated with the delegate.
        """
        if user_id in self.users and "delegate" in self.users[user_id]:
            return self.users[user_id]["delegate"]["token"] == delegate_token and self.users[user_id]["delegate"]["case"] == case_id
        else:
            return False
