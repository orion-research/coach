"""
Example estimation method that takes two parameters and returns the average of them.
"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

import json


from COACH.framework.coach import endpoint, EstimationMethodService

class AverageOfTwo(EstimationMethodService):
    """
    This is a simple example of an estimation method.
    It takes two parameters, X and Y, and the result is the average of them.
    """
    
    def parameter_names(self):
        return ["x", "y"]
    
    
    @endpoint("/info", ["GET", "PUT"], "text/plain")
    def info(self):
        return "This is an estimation method which takes two parameters (X, Y), and returns the average of the result."
    
    
    @endpoint("/evaluate", ["GET", "PUT"], "application/json")
    def evaluate(self, x, y):
        result = (float(x) + float(y)) / 2.0
        print("** evaluate( x = " + str(x) + ", y = " + str(y) + ") = " + str(result))
        return json.dumps(result)


if __name__ == '__main__':
    AverageOfTwo(sys.argv[1]).run()
