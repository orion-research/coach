'''
Created on 7 juin 2017

@author: francois
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import endpoint, EstimationMethodService

class BasicCOCOMO(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) != 2 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        return float(parameters_dict["a"]) * float(properties_dict["KLOC"]) ** float(parameters_dict["b"])
    
if __name__ == '__main__':
    BasicCOCOMO(sys.argv[1]).run()
