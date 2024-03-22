#!/bin/bash

set -e

# Wait for the database to start
until pypgstac pgready --dsn postgresql://username:password@0.0.0.0:5432/postgis; do
  echo "Waiting for database to start..."
  sleep 1
done

# Load collections
echo "Loading collections..."
pypgstac load collections /tmp/data/noaa-emergency-response.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method upsert

# Load items
echo "Loading items..."
pypgstac load items /tmp/data/noaa-eri-nashville2020.json --dsn postgresql://username:password@0.0.0.0:5432/postgis --method upsert

# Load tipg features
echo "Loading features..."
DSN="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB"
psql $DSN -f /tmp/data/mydata.sql

echo "Data loaded successfully!"
