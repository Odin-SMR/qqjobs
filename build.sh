#!/bin/bash

# This script is run by jenkins jobs that uses the build master template job.

set -e

docker build -t docker2.molflow.com/devops/microq_admin .
if [ "$#" -ge 1 ]
then
	if [ "$1" == "--local" ]; then
    echo "Local build, no pushing"
    exit
  fi
fi
docker push docker2.molflow.com/devops/microq_admin
