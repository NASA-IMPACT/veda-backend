export STAC_API_URL="https://xnv4kvaonc.execute-api.us-west-2.amazonaws.com/api/stac/"
export STAGE_NAME="dev"
export APP_NAME="veda-stac-browser"

AWS_PROFILE=853558080719_AdministratorAccess cdk deploy --app "python3 app.py" --all --require-approval never