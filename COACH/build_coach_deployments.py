'''
This is a script used to generate the deployment files for the COACH installations
within the ORION project.

Created on 18 nov. 2016

@author: Jakob Axelsson
'''

from COACH.deployment import *

# Services to be deployed

# Decision process services
simple = DecisionProcessService("SimpleDecisionProcessService", "A decision process service",
                                "decision_process.SimpleDecisionProcessService")
pugh = DecisionProcessService("PughService", "Pugh analysis", "decision_process.PughService")

# Estimation method services
average_of_two = EstimationMethodService("AverageOfTwo", "Average of two estimation method",
                                         "estimation_method.AverageOfTwo")
expert_opinion = EstimationMethodService("ExpertOpinion", "Expert opinion estimation method",
                                         "estimation_method.ExpertOpinion")

expert_estimate_text = EstimationMethodService("ExpertEstimateText", "ExpertEstimateText estimation method",
                                               "estimation_method.expert_estimate_text")

expert_estimate_float = EstimationMethodService("ExpertEstimateFloat", "ExpertEstimateFloat estimation method",
                                                "estimation_method.expert_estimate_float")

expert_estimate_integer = EstimationMethodService("ExpertEstimateInteger", "ExpertEstimateInteger estimation method",
                                                  "estimation_method.expert_estimate_integer")

basic_COCOMO = EstimationMethodService("BasicCOCOMO", "BasicCOCOMO estimation method",
                                       "estimation_method.basic_cocomo")

intermediate_COCOMO = EstimationMethodService("IntermediateCOCOMO", "IntermediateCOCOMO estimation method",
                                              "estimation_method.intermediate_cocomo")

cost_estimation = EstimationMethodService("CostEstimation", "CostEstimation estimation method",
                                          "estimation_method.cost_estimation")


# TODO: Add BaseTest here


# Authentication service
authentication = AuthenticationService("AuthenticationService", "Authentication service for COACH", "framework",
                                       "settings/authentication.json", 
                                       {"server": "send.one.com", "port": 587, "sender": "noreply@orion-research.se"})

# Context model services
context_model = ContextModelService("ContextModelService", "A context model service for COACH",
                                    "context_model")

# Property model services
property_model = PropertyModelService("PropertyModelService", "A property model service for COACH",
                                    "property_model")

# Knowledge repository services
knowledge_repository = KnowledgeRepositoryService("KnowledgeRepositoryService", 
                                                  "Knowledge repository microservice for the ORION project", 
                                                  "knowledge_repository", 
                                                  "http://127.0.0.1:7474/db/data/",
                                                  authentication)
 
# Case database
database = CaseDatabase("CaseDatabase", "COACH case database service", "framework", "CaseDB", authentication,
                        knowledge_repository)
 
# Directory services
services_listed_in_directory = [simple, pugh, average_of_two, expert_opinion, database, knowledge_repository]

directory = DirectoryService("DirectoryService", "Directory service for COACH", "framework",
                             services_listed_in_directory) 

# Knowledge inference service
knowledge_inference = KnowledgeInferenceService("KnowledgeInferenceService",
                                                "Knowledge inference microservice for the ORION project",
                                                "framework",
                                                database,
                                                directory) 


# Interaction service
root = InteractionService("InteractionService", "COACH interaction microservice for ORION project", "framework",
                          database, [directory], authentication,
                          knowledge_repository, context_model, property_model)


all_services = [services_listed_in_directory] + [root, directory, context_model, property_model]

# Configurations on which the services will be deployed

services_with_ports = {directory : 5003,
                       context_model : 5006,
                       property_model : 5011,
                       knowledge_repository : 5005,
                       simple : 5002,
                       pugh : 5007,
                       average_of_two : 5004,
                       expert_opinion : 5001,
                       database: 5008, 
                       authentication : 5009,
                       knowledge_inference : 5010,
                       expert_estimate_text : 5012,
                       expert_estimate_float : 5013,
                       expert_estimate_integer : 5014,
                       basic_COCOMO : 5015,
                       intermediate_COCOMO : 5016,
                       cost_estimation: 5017}

local_services_with_ports = services_with_ports.copy()
local_services_with_ports[root] = 5000

local = LocalConfiguration("local", "127.0.0.1", local_services_with_ports, "http", "local_settings.json")  

development_services_with_ports = services_with_ports.copy()
development_services_with_ports[root] = 443

development = ApacheConfiguration("development", "orion.sics.se", development_services_with_ports, "https",
                                  "development_settings.json", "jax", "www-data", "3.5")

configurations = [local, development]


def main():
    print("Executing script " + __file__ + "\n")

    for c in configurations:
        print("Generating " + c.mode + " configuration")
        c.generate(__file__)


if __name__ == "__main__":
    main()


