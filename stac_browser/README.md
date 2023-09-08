## VEDA STAC browser CDK app

## Description

This folder hosts the CDK code used to deploy AWS resources to host a [STAC browser](https://github.com/radiantearth/stac-browser) pointing to the VEDA STAC catalog. It relies on the [eoapi-cdk](https://github.com/developmentseed/eoapi-cdk) STAC browser CDK construct. It should be deployed _after_ the [main veda-backend](https://github.com/NASA-IMPACT/veda-backend) CloudFormation app because it relies on the STAC API URL to be already deployed. 

Operate with as a current directory the folder of this README.

## Environment

- `STAC_API_URL` **required. The veda-backend must be already deployed.**
- `STAGE_NAME` **required** 
- `APP_NAME` **required** 

## Installation

```
python -m venv .browser_deployment_venv
source .browser_deployment_venv/bin/activate
python -m pip install -r requirements.txt
```

## Authentication

Authenticate your CLI to the AWS account you're deploying to. 

## Deployment

```
cdk deploy --app "python3 app.py" --all --require-approval never
```