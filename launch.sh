#!/bin/bash

echo "Starting root server and directory server..."
cd COACH/framework
nohup python3 launch.py $1 $2 $3 &

echo "Starting SimpleDecisionModelService..."
cd ../decision_process/SimpleDecisionProcessService
nohup python3 SimpleDecisionProcessService.py &

echo "Starting ExpertOpinion estimation method service..."
cd ../../estimation_method/ExpertOpinion
nohup python3 ExpertOpinion.py &

echo "Starting AverageOfTwo estimation method service..."
cd ../AverageOfTwo
nohup python3 AverageOfTwo.py &

echo "Done initializing services!" 