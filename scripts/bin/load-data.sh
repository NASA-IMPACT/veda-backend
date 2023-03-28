#!/bin/bash

set -e

# Wait for the database to start
until pg_isready -h 0.0.0.0 -p 5432 -U username; do
  echo "Waiting for database to start..."
  sleep 1
done

# Load collections
echo "Loading collections..."
pypgstac pgready --dsn postgresql://username:password@0.0.0.0:5432/postgis
pypgstac load collections /tmp/data/noaa-emergency-response.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method insert

# Load items
echo "Loading items..."
pypgstac load items /tmp/data/noaa-eri-nashville2020.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method insert

echo "Data loaded successfully!"
