'''
Created on 7 juin 2017

@author: francois
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import endpoint, EstimationMethodService

class ExpertEstimateFloat(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) != 1 or len(properties_dict) != 0:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        return float(parameters_dict["estimation"])
    
if __name__ == '__main__':
    ExpertEstimateFloat(sys.argv[1]).run()
