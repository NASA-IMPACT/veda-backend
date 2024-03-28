#!/bin/bash

set -e

# Wait for the database to start
until pypgstac pgready --dsn postgresql://username:password@0.0.0.0:5432/postgis; do
  echo "Waiting for database to start..."
  sleep 1
done

# Load collections
echo "Loading collections..."
pypgstac load collections /tmp/data/nightlights-500m-daily.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method upsert

# Load items
echo "Loading items..."
pypgstac load items /tmp/data/nightlights-500m-daily-items.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method upsert

echo "Data loaded successfully!"
