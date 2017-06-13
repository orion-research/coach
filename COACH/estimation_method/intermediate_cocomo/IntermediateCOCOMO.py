'''
Created on 8 juin 2017

@author: francois
'''

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.framework.coach import endpoint, EstimationMethodService

class IntermediateCOCOMO(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) !=17 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        result = float(parameters_dict["a"]) * float(properties_dict["KLOC"]) ** float(parameters_dict["b"])
        parameters = ["RELY", "DATA", "CPLX", "TIME", "STOR", "VIRT", "TURN", "ACAP", "AEXP", "PCAP", "VEXP", "LEXP", "MODP", "TOOL", "SCED"]
        for parameter in parameters:
            result *= float(parameters_dict[parameter])
        return result;
    
if __name__ == '__main__':
    IntermediateCOCOMO(sys.argv[1]).run()