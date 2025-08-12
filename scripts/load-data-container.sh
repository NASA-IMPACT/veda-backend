#!/bin/bash

DOCKER_CONTAINER_NAME="veda.db"
SCRIPT_PATH="/tmp/scripts/bin/load-data.sh"

docker exec veda.loadtestdata "$DOCKER_CONTAINER_NAME" "$SCRIPT_PATH"
