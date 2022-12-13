#!/usr/bin/env bash
# Use this script to load environment variables for a deployment from AWS Secrets

echo Loading environment secrets from $1
aws secretsmanager get-secret-value --secret-id $1 --query SecretString --output text | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' > .env
