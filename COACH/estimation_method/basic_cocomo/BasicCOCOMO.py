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
        if len(parameters_dict) != 1 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        if parameters_dict["developmentMode"] == "Organic":
            a = 2.4
            b = 1.05
        elif parameters_dict["developmentMode"] == "Semi-detached":
            a = 3.0
            b = 1.12
        elif parameters_dict["developmentMode"] == "Embedded":
            a = 3.6
            b = 1.20
        else:
            raise RuntimeError("Name provided for the parameter developmentMode is unknown : " + parameters_dict["developmentMode"]
                               + ". Allowed names are 'Organic', 'Semi-detached' and 'Embedded'")
            
        return a * float(properties_dict["KLOC"]) ** b
    
if __name__ == '__main__':
    BasicCOCOMO(sys.argv[1]).run()
