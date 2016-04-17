"""
Example estimation method which captures expert opinion, i.e. it takes one parameter which is also the result of the estimation.
"""

from COACH.framework import coach


class ExpertOpinion(coach.EstimationMethod):
    """
    This is a simple example of an estimation method.
    It takes one parameter, and just returns it.
    """
    
    def info(self, params):
        return "This is an estimation method which takes one parameters (X), and returns it."
    
    
    def parameter_names(self):
        return ["x"]
    
    
    def evaluate(self, params):
        return str(float(params["x"]))


if __name__ == '__main__':
    coach.EstimationMethodService("settings/expert_opinion_settings.json", ExpertOpinion)
