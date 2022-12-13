# veda-backend
This project deploys a complete backend for a [SpatioTemporal Asset Catalog](https://stacspec.org/) including a postgres database, a metadata API, and raster tiling API. Veda-backend is a non-forked version of the [eoAPI](https://github.com/developmentseed/eoAPI) demo project. Veda-backend is decoupled from the demo project to selectively incorporate new stable functionality from the fast moving development in eoAPI while providing a continuous baseline for veda-backend users and to support project specific business and deployment logic.

The primary tools employed in the [eoAPI demo](https://github.com/developmentseed/eoAPI) and this project are:
- [stac-spec](https://github.com/radiantearth/stac-spec)
- [stac-api-spec](https://github.com/radiantearth/stac-api-spec)
- [stac-fastapi](https://github.com/stac-utils/stac-fastapi)
- [pgstac](https://github.com/stac-utils/pgstac)
- [titiler](https://github.com/developmentseed/titiler)
- [titiler-pgstac](https://github.com/stac-utils/titiler-pgstac)

![architecture diagram](.readme/veda-backend.svg)

## Deployment

This repo includes CDK scripts to deploy a PgStac AWS RDS database and other resources to support APIs maintained by the VEDA backend development team.

### Tooling & supporting documentation

- [CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)

### Enviroment variables

An [.example.env](.example.env) template is supplied for for local deployments. If updating an existing deployment, it is essential to check the most current values for these variables by fetching these values from AWS Secrets Manager. The environment secrets are named `<app-name>-backend/<stage>-env`, for example `veda-backend/dev-env`.

### Fetch environment variables using AWS CLI

To retrieve the variables for a stage that has been previously deployed, the secrets manager can be used to quickly populate an .env file. 
> Note: The environment variables stored as AWS secrets are manually maintained and should be reviewed before using.

```
export AWS_SECRET_ID=<app-name>-backend/<stage>-env

aws secretsmanager get-secret-value --secret-id ${AWS_SECRET_ID} --query SecretString --output text | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' > .env
```

| Name | Explanation |
| --- | --- |
| `APP_NAME` | Optional app name used to name stack and resources, defaults to `veda` |
| `STAGE` | **REQUIRED** Deployment stage used to name stack and resources, i.e. `dev`, `staging`, `prod` |
| `VPC_ID` | Optional resource identifier of VPC, if none a new VPC with public and private subnets will be provisioned. |
| `PERMISSIONS_BOUNDARY_POLICY_NAME` | Optional name of IAM policy to define stack permissions boundary |
| `CDK_DEFAULT_ACCOUNT` | When deploying from a local machine the AWS account id is required to deploy to an exiting VPC |
| `CDK_DEFAULT_REGION` | When deploying from a local machine the AWS region id is required to deploy to an exiting VPC |
| `VEDA_DB_PGSTAC_VERSION` | **REQUIRED** version of PgStac database, i.e. 0.5 |
| `VEDA_DB_SCHEMA_VERSION` | **REQUIRED** The version of the custom veda-backend schema, i.e. 0.1.1 |
| `VEDA_DB_SNAPSHOT_ID` | **Once used always REQUIRED** Optional RDS snapshot identifier to initialize RDS from a snapshot |
| `VEDA_DB_PRIVATE_SUBNETS` | Optional boolean to deploy database to private subnet |
| `VEDA_DOMAIN_HOSTED_ZONE_ID` | Optional Route53 zone identifier if using a custom domain name |
| `VEDA_DOMAIN_HOSTED_ZONE_NAME` | Optional custom domain name, i.e. veda-backend.xyz |
| `VEDA_DOMAIN_ALT_HOSTED_ZONE_ID` | Optional second Route53 zone identifier if using a custom domain name |
| `VEDA_DOMAIN_ALT_HOSTED_ZONE_NAME` | Optional second custom domain name, i.e. alt-veda-backend.xyz |
| `VEDA_DOMAIN_API_PREFIX` | Optional domain prefix override supports using a custom prefix instead of the STAGE variabe (an alternate version of the stack can be deployed with a unique STAGE=altprod and after testing prod API traffic can be cut over to the alternate version of the stack by setting the prefix to prod) |
| `VEDA_RASTER_ENABLE_MOSAIC_SEARCH` | Optional deploy the raster API with the mosaic/list endpoint TRUE/FALSE |
| `VEDA_RASTER_DATA_ACCESS_ROLE_ARN` | Optional arn of IAM Role to be assumed by raster-api for S3 bucket data access, if not provided default role for the lambda construct is used |

### Deploying to the cloud

#### Install pre-requisites

```bash
nvm install 17
nvm use 17
node --version
npm install --location=global aws-cdk
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,deploy,test]"
```

#### Run the deployment

```
# Review what infrastructure changes your deployment will cause
cdk diff
# Execute deployment, security changes will require approval for deployment
cdk deploy
```

#### Check CloudFormation deployment status

After logging in to the console at https://<account number>.signin.aws.amazon.com/console the status of the CloudFormation stack can be viewed here: https://<aws-region>.console.aws.amazon.com/cloudformation/home.
  
## Deleting the CloudFormation stack

If this is a development stack that is safe to delete, you can delete the stack in CloudFormation console or via `cdk destroy`, however, the additional manual steps were required to completely delete the stack resources:

1. You will need to disable deletion protection of the RDS database and delete the database.
2. Detach the Internet Gateway (IGW) from the VPC and delete it.
3. If this stack created a new VPC, delete the VPC (this should delete a subnet and security group too).

## Deployment to MCP and/or an existing VPC
  
### MCP access

  At this time, this project requires that anyone deploying to the Mission Cloud Platform (MCP) environments should have gone through a NASA credentialing process and then submitted and gotten approval for access to the VEDA project on MCP.

### MCP and existing VPC endpoint requirements

VPC interface endpoints must be configured to allow app components to connect to other services within the VPC and gateway endpoints need to be configured for external connections.

| service-name | vpc-endpoint-type | comments |
| -- | -- | -- |
| secretsmanager | Interface | security group configuration recommendations below |
| logs | Interface | cloudwatch-logs, security group configuration recommendations below |
| s3 | Gateway |  |
| dynamodb | Gateway | required if using DynamoDB streams |

### Create `Interface` VPC endpoints
Create a security group for the VPC Interface endpoints ([AWS docs](https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-sg.html)) 
```bash
aws ec2 create-security-group --vpc-id <vpc-id> --group-name vpc-interface-endpoints --description "security group for vpc interface endpoints"
```
Configure ingress policy for this SG (the egress is configured for 'free' when a new SG is created)
```bash
# Lookup CidrBlock 
aws ec2 describe-vpcs --vpc-ids $VPC_ID | jq -r '.Vpcs[].CidrBlock'

aws ec2 authorize-security-group-ingress --group-id <new sg just created above> --protocol tcp --port 443 --cidr <cidr range>
```
Create VPC Interface endpoints
```
# Choose private subnets (example subnet was generated by aws-cdk)
aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc-id> Name=tag:aws-cdk:subnet-name,Values=private | jq -r '.Subnets[].SubnetId'

# Secrets manager endpoint
aws ec2 create-vpc-endpoint \
--vpc-id <vpc-id> \
--vpc-endpoint-type Interface \
--service-name com.amazonaws.us-west-2.secretsmanager \
--subnet-ids <private subnet> <private subnet> \
--security-group-ids <new sg just created above>

# Cloudwatch logs endpoint uses same security group cfg
aws ec2 create-vpc-endpoint \
--vpc-id <vpc-id> \
--vpc-endpoint-type Interface \
--service-name com.amazonaws.us-west-2.logs \
--subnet-ids <private subnet> <private subnet> \
--security-group-ids <new sg just created above>
```

### Create `Gateway` VPC endpoints
```
# List route tables for VPC
aws ec2 describe-route-tables --filters Name=vpc-id,Values=<vpc-id> | jq -r '.RouteTables[].RouteTableId'

# Create Gateway endpoint for S3 
aws ec2 create-vpc-endpoint \
--vpc-id <vpc-id> \
--vpc-endpoint-type Gateway \
--service-name com.amazonaws.us-west-2.s3 \
--route-table-ids <route table ids for each subnet in vpc>

# Optional create Gateway endpoint for DynamoDB
aws ec2 create-vpc-endpoint \
--vpc-id <vpc-id> \
--vpc-endpoint-type Gateway \
--service-name com.amazonaws.us-west-2.dynamodb \
--route-table-ids <route table ids for each subnet in vpc>
```

## [OPTIONAL] Deploy standalone base infrastructure
For convenience, [standalone base infrastructure](standalone_base_infrastructure/README.md#standalone-base-infrastructure) scripts are provided to deploy base infrastructure to simulate deployment in a controlled environment.

## Local Docker deployment

Start up a local stack
```
docker compose up
```
Clean up after running locally
```
docker compose down
```

# Operations

## Ingesting metadata
STAC records should be loaded using [pypgstac](https://github.com/stac-utils/pgstac#pypgstac). The [cloud-optimized-data-pipelines](https://github.com/NASA-IMPACT/cloud-optimized-data-pipelines) project provides examples of cloud pipelines that use pypgstac to load data into a STAC catalog, as well as examples of transforming data to cloud optimized formats.

## Support scripts
Support scripts are provided for manual system operations.
- [Rotate pgstac password](support_scripts/README.md#rotate-pgstac-password)
## Usage examples: 

https://github.com/NASA-IMPACT/veda-documentation
# STAC community resources

## STAC browser
Radiant Earth's [stac-browser](https://github.com/radiantearth/stac-browser) is a browser for STAC catalogs. The demo version of this browser [radiantearth.github.io/stac-browser](https://radiantearth.github.io/stac-browser/#/) can be used to browse the contents of the veda-backend STAC catalog, paste the veda-backend stac-api URL deployed by this project in the demo and click load. Read more about the recent developments and usage of stac-browser [here](https://medium.com/radiant-earth-insights/the-exciting-future-of-the-stac-browser-2351143aa24b).

# License
This project is licensed under **Apache 2**, see the [LICENSE](LICENSE) file for more details.