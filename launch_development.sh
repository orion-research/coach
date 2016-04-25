#!/bin/bash

# Check number of arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: ./launch.sh <database user name> <database password> <secret key>"
    exit 1
fi

# Delete output from previous run of services
find . -name "nohup.out" -delete

echo "Starting root server and directory server..."
cd COACH/framework
nohup python3 launch.py settings/root_settings_development.json settings/directory_settings_development.json $1 $2 $3 &

echo "Starting SimpleDecisionModelService..."
cd ../decision_process/SimpleDecisionProcessService
nohup python3 SimpleDecisionProcessService.py settings/decision_process_settings_development.json &

echo "Starting ExpertOpinion estimation method service..."
cd ../../estimation_method/ExpertOpinion
nohup python3 ExpertOpinion.py settings/expert_opinion_settings_development.json &

echo "Starting AverageOfTwo estimation method service..."
cd ../AverageOfTwo
nohup python3 AverageOfTwo.py settings/average_of_two_settings_development.json &

echo "Done initializing services!" 
