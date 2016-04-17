"""
Example estimation method that takes two parameters and returns the average of them.
"""

from COACH.framework import coach

class AverageOfTwo(coach.EstimationMethod):
    """
    This is a simple example of an estimation method.
    It takes two parameters, X and Y, and the result is the average of them.
    """
    
    def info(self, params):
        return "This is an estimation method which takes two parameters (X, Y), and returns the average of the result."
    
    
    def parameter_names(self):
        return ["x", "y"]
    
    
    def evaluate(self, params):
        return str((float(params["x"]) + float(params["y"])) / 2.0)


if __name__ == '__main__':
    coach.EstimationMethodService("settings/average_of_two_settings.json", AverageOfTwo)
