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

class IntermediateCOCOMO(EstimationMethodService):
    
    @endpoint("/compute", ["POST"], "application/json")
    def compute(self, parameters_dict, properties_dict):
        if len(parameters_dict) !=16 or len(properties_dict) != 1:
            raise RuntimeError("Provided parameters does not match with the ontology")
        
        if parameters_dict["developmentMode"] == "Organic":
            b = 1.05
        elif parameters_dict["developmentMode"] == "Semi-detached":
            b = 1.12
        elif parameters_dict["developmentMode"] == "Embedded":
            b = 1.20
        else:
            raise RuntimeError("Name provided for the parameter developmentMode is unknown : " + parameters_dict["developmentMode"]
                               + ". Allowed names are 'Organic', 'Semi-detached' and 'Embedded'")
        
        result = float(properties_dict["KLOC"]) ** b
        parameters_table = self._create_parameters_table()
        for parameter in parameters_dict:
            result *= parameters_table[parameter][parameters_dict[parameter]]
        return result;
    
    def _create_parameters_table(self):
        parameters_table = {}
        parameters_table["RELY"] = {
                                        "Very low": 0.75,
                                        "Low": 0.88,
                                        "Nominal": 1.0,
                                        "High": 1.15,
                                        "Very high": 1.40
                                    }
        
        parameters_table["DATA"] = {
                                        "Low": 0.94,
                                        "Nominal": 1.0,
                                        "High": 1.08,
                                        "Very high": 1.16
                                    }
        
        parameters_table["CPLX"] = {
                                        "Very low": 0.70,
                                        "Low": 0.85,
                                        "Nominal": 1.0,
                                        "High": 1.15,
                                        "Very high": 1.30,
                                        "Extra high": 1.65
                                    }
        
        parameters_table["TIME"] = {
                                        "Nominal": 1.0,
                                        "High": 1.11,
                                        "Very high": 1.30,
                                        "Extra high": 1.66
                                    }
        
        parameters_table["STOR"] = {
                                        "Nominal": 1.0,
                                        "High": 1.06,
                                        "Very high": 1.21,
                                        "Extra high": 1.56
                                    }
        
        parameters_table["VIRT"] = {
                                        "Low": 0.87,
                                        "Nominal": 1.0,
                                        "High": 1.15,
                                        "Very high": 1.30
                                    }
        
        parameters_table["TURN"] = {
                                        "Low": 0.87,
                                        "Nominal": 1.0,
                                        "High": 1.07,
                                        "Very high": 1.15
                                    }
        
        parameters_table["ACAP"] = {
                                        "Very low": 1.46,
                                        "Low": 1.19,
                                        "Nominal": 1.0,
                                        "High": 0.86,
                                        "Very high": 0.71
                                    }
        
        parameters_table["AEXP"] = {
                                        "Very low": 1.29,
                                        "Low": 1.13,
                                        "Nominal": 1.0,
                                        "High": 0.91,
                                        "Very high": 0.82
                                    }
        
        parameters_table["PCAP"] = {
                                        "Very low": 1.42,
                                        "Low": 1.17,
                                        "Nominal": 1.0,
                                        "High": 0.86,
                                        "Very high": 0.70
                                    }
        
        parameters_table["VEXP"] = {
                                        "Very low": 1.21,
                                        "Low": 1.10,
                                        "Nominal": 1.0,
                                        "High": 0.90,
                                    }
        
        parameters_table["LEXP"] = {
                                        "Very low": 1.14,
                                        "Low": 1.07,
                                        "Nominal": 1.0,
                                        "High": 0.95,
                                    }
        
        parameters_table["MODP"] = {
                                        "Very low": 1.24,
                                        "Low": 1.10,
                                        "Nominal": 1.0,
                                        "High": 0.91,
                                        "Very high": 0.82
                                    }
        
        parameters_table["TOOL"] = {
                                        "Very low": 1.24,
                                        "Low": 1.10,
                                        "Nominal": 1.0,
                                        "High": 0.91,
                                        "Very high": 0.83
                                    }
        
        parameters_table["SCED"] = {
                                        "Very low": 1.23,
                                        "Low": 1.08,
                                        "Nominal": 1.0,
                                        "High": 1.04,
                                        "Very high": 1.10
                                    }
        
        parameters_table["developmentMode"] = {
                                        "Organic": 2.4,
                                        "Semi-detached": 3.0,
                                        "Embedded": 3.6,
                                    }
        return parameters_table
    
if __name__ == '__main__':
    IntermediateCOCOMO(sys.argv[1]).run()