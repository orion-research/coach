'''
Created on 17 apr. 2016

@author: Jakob Axelsson
'''

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir))

from COACH.framework import coach
from COACH.decision_process.SimpleDecisionProcessService import SimpleDecisionProcessService
from COACH.decision_process.PughService import PughService
from COACH.context_model import ContextModelService
from COACH.estimation_method.AverageOfTwo import AverageOfTwo
from COACH.estimation_method.ExpertOpinion import ExpertOpinion
from COACH.knowledge_repository import knowledge_repository


if __name__ == '__main__':
    try:
        # This will work if running script from command line (Windows or Linux)
        # For some reason, it does not work if starting from within Eclipse
        topdir = os.path.abspath(os.curdir)
        
        # Start root service and directory service from the framework module
        wdir = os.path.join(topdir, "framework")
        os.chdir(wdir)
    except:
        # Workaround for starting in Eclipse
        topdir = os.path.join(os.path.abspath(os.curdir), "COACH")

        # Start root service and directory service from the framework module
        wdir = os.path.join(topdir, "framework")
        os.chdir(wdir)
        
    coach.RootService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                      os.path.normpath("settings/root_secret_data.json"),
                      working_directory = wdir).run()
    coach.DirectoryService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                           working_directory = os.path.join(topdir, "framework")).run()
    knowledge_repository.KnowledgeRepositoryService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                                                    os.path.normpath("settings/root_secret_data.json"),
                                                    working_directory = wdir).run()
 

    # Start the decision process services
    wdir = os.path.join(topdir, os.path.normpath("decision_process/SimpleDecisionProcessService"))
    os.chdir(wdir)
    SimpleDecisionProcessService.SimpleDecisionProcessService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                                                              working_directory = wdir).run()
    
    wdir = os.path.join(topdir, os.path.normpath("decision_process/PughService"))
    os.chdir(wdir)
    PughService.PughService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                            working_directory = wdir).run()
    
    # Start the context model service
    wdir = os.path.join(topdir, os.path.normpath("context_model"))
    os.chdir(wdir)
    ContextModelService.ContextModelService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                                                              working_directory = wdir).run()
    
    # Start the estimation method services
    wdir = os.path.join(topdir, os.path.normpath("estimation_method/AverageOfTwo"))
    os.chdir(wdir)
    coach.EstimationMethodService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                                  handling_class = AverageOfTwo.AverageOfTwo,
                                  working_directory = wdir).run()

    wdir = os.path.join(topdir, os.path.normpath("estimation_method/ExpertOpinion"))
    os.chdir(wdir)
    coach.EstimationMethodService(os.path.join(topdir, os.path.normpath("local_settings.json")), 
                                  handling_class = ExpertOpinion.ExpertOpinion,
                                  working_directory = wdir).run()
