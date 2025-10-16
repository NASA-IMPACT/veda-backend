#!/bin/bash

set -e

DATA_DIR=/tmp/data
collections=(
    "${DATA_DIR}/noaa-emergency-response.json"
    "${DATA_DIR}/barc-thomasfire.json"
    "${DATA_DIR}/caldor-fire-behavior.json"
    "${DATA_DIR}/CMIP245-winter-median-pr.json"
)
items=(
    "${DATA_DIR}/noaa-eri-nashville2020.json"
    "${DATA_DIR}/barc-thomasfire-items.json"
    "${DATA_DIR}/caldor-fire-behavior-items.json"
    "${DATA_DIR}/CMIP245-winter-median-pr-items.json"
)

# Wait for the database to start
until pypgstac pgready; do
  echo "Waiting for database to start..."
  sleep 1
done


# Load collections
echo "Loading collections..."

for collection in "${collections[@]}"; do
    echo "Loading collection: ${collection}"
    pypgstac load collections ${collection} --method upsert
    echo "Successfully loaded collection: ${collection}"
done

# Load items
echo "Loading items..."

for item in "${items[@]}"; do
    echo "Loading items: ${item}"
    pypgstac load items ${item} --method upsert
    echo "Successfully loaded items: ${item}"
done

echo "Data loaded successfully!"
