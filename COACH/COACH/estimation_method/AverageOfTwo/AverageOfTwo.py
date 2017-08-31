
# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from flask import Response

# Coach framework
from COACH.framework.coach import endpoint, EstimationMethodService

class AverageOfTwo(EstimationMethodService):
    
    def parameter_names(self):
        # If the estimation method has no parameters, this method can be removed.
        return []
    
    
    @endpoint("/info", ["GET", "PUT"])
    def info(self):
        return Response("This is a template for estimation methods. It currently takes no parameters, and always returns 0.")
    
    
    @endpoint("/evaluate", ["GET", "PUT"])
    def evaluate(self, params):
        return Response(str(0))


if __name__ == '__main__':
    AverageOfTwo().run()
