'''
Created on 17 apr. 2016

@author: Jakob Axelsson
'''

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir))

from COACH.framework import coach
from COACH.decision_process.SimpleDecisionProcessService import SimpleDecisionProcessService
from COACH.estimation_method.AverageOfTwo import AverageOfTwo
from COACH.estimation_method.ExpertOpinion import ExpertOpinion

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
        
    coach.RootService(os.path.normpath("settings/root_settings_development.json"), 
                      os.path.normpath("settings/root_secret_data.json"),
                      working_directory = wdir).run()
    coach.DirectoryService(os.path.normpath("settings/directory_settings_development.json"), 
                           working_directory = os.path.join(topdir, "framework")).run()
 

    # Start the decision process service
    wdir = os.path.join(topdir, os.path.normpath("decision_process/SimpleDecisionProcessService"))
    os.chdir(wdir)
    SimpleDecisionProcessService.SimpleDecisionProcessService(os.path.normpath("settings/decision_process_settings_development.json"),
                                                              working_directory = wdir).run()
    
    # Start the estimation method services
    wdir = os.path.join(topdir, os.path.normpath("estimation_method/AverageOfTwo"))
    os.chdir(wdir)
    coach.EstimationMethodService(os.path.normpath("settings/average_of_two_settings_development.json"), 
                                  handling_class = AverageOfTwo.AverageOfTwo,
                                  working_directory = wdir).run()

    wdir = os.path.join(topdir, os.path.normpath("estimation_method/ExpertOpinion"))
    os.chdir(wdir)
    coach.EstimationMethodService(os.path.normpath("settings/expert_opinion_settings_development.json"), 
                                  handling_class = ExpertOpinion.ExpertOpinion,
                                  working_directory = wdir).run()
