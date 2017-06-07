'''
Created on 7 juin 2017

@author: francois
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

import json


from COACH.framework.coach import endpoint, EstimationMethodService

class COCOMO(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) != 2 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        return int(parameters_dict["a"]) * int(properties_dict["KLOC"]) ** int(parameters_dict["b"])
    
if __name__ == '__main__':
    COCOMO(sys.argv[1]).run()
