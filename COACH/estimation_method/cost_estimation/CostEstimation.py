'''
Created on 8 juin 2017

@author: francois
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import endpoint, EstimationMethodService

# TODO: to suppress
from datetime import datetime
import inspect

def log(*args):
    message = datetime.now().strftime("%H:%M:%S") + " : "
    message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg) + " "
    print(message)
    sys.stdout.flush()

class CostEstimation(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) != 1 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        return float(parameters_dict["Salary"]) * float(properties_dict["DevelopmentEffort"])
    
if __name__ == '__main__':
    CostEstimation(sys.argv[1]).run()