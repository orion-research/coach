# This file was automatically generated by the C:\Users\Jakob Axelsson\Documents\Arbetsdokument\Eclipse workspace\COACH\COACH\build_coach_deployments.py script on <module 'datetime' from 'C:\\Python34\\lib\\datetime.py'>.

import os
import sys

sys.path.append(os.path.join(os.curdir, os.pardir))

from COACH.framework import coach
from COACH.knowledge_repository import KnowledgeRepositoryService
from COACH.framework.casedb import CaseDatabase
from COACH.estimation_method.AverageOfTwo import AverageOfTwo
from COACH.framework.DirectoryService import DirectoryService
from COACH.framework.KnowledgeInferenceService import KnowledgeInferenceService
from COACH.framework.AuthenticationService import AuthenticationService
from COACH.framework.InteractionService import InteractionService
from COACH.estimation_method.ExpertOpinion import ExpertOpinion
from COACH.decision_process.SimpleDecisionProcessService import SimpleDecisionProcessService
from COACH.decision_process.PughService import PughService
from COACH.context_model import ContextModelService
from COACH.property_model import PropertyModelService

if __name__ == '__main__':
    # Start all the services
    
    KnowledgeRepositoryService.KnowledgeRepositoryService().run()

    CaseDatabase().run()
    
    AverageOfTwo.AverageOfTwo().run()
    
    DirectoryService().run()
    
    KnowledgeInferenceService().run()

    AuthenticationService().run()

    InteractionService().run()
    
    ExpertOpinion.ExpertOpinion().run()
    
    SimpleDecisionProcessService.SimpleDecisionProcessService().run()
    
    PughService.PughService().run()
    
    ContextModelService.ContextModelService().run()
    
    PropertyModelService.PropertyModelService().run()
