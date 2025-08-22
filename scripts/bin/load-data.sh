#!/bin/bash

set -e

# Wait for the database to start
until pypgstac pgready; do
  echo "Waiting for database to start..."
  sleep 1
done

# Load collections
echo "Loading collections..."
pypgstac load collections /tmp/data/noaa-emergency-response.json --method upsert

# Load items
echo "Loading items..."
pypgstac load items /tmp/data/noaa-eri-nashville2020.json --method upsert

echo "Data loaded successfully!"
