#!/usr/bin/env bash
# Use this script to load environment variables for a deployment from AWS Secrets

for s in $(aws secretsmanager get-secret-value --secret-id $1 --query SecretString --output text | jq -r "to_entries|map(\"\(.key)=\(.value|tostring)\")|.[]" ); do
    echo "$s" >> $GITHUB_ENV
done
