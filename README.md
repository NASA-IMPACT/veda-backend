# veda-backend

This project deploys a complete backend for a [SpatioTemporal Asset Catalog](https://stacspec.org/) including a postgres database, a metadata API, and raster tiling API. Veda-backend is a non-forked version of the [eoAPI](https://github.com/developmentseed/eoAPI) demo project. Veda-backend is decoupled from the demo project to selectively incorporate new stable functionality from the fast moving development in eoAPI while providing a continuous baseline for veda-backend users and to support project specific business and deployment logic.

The primary tools employed in the [eoAPI demo](https://github.com/developmentseed/eoAPI) and this project are:

- [stac-spec](https://github.com/radiantearth/stac-spec)
- [stac-api-spec](https://github.com/radiantearth/stac-api-spec)
- [stac-fastapi](https://github.com/stac-utils/stac-fastapi)
- [pgstac](https://github.com/stac-utils/pgstac)
- [titiler](https://github.com/developmentseed/titiler)
- [titiler-pgstac](https://github.com/stac-utils/titiler-pgstac)
- [eoapi-cdk](https://github.com/developmentseed/eoapi-cdk/tree/main#eoapi-cdk-constructs) + [radiantearth/stac-browser](https://github.com/radiantearth/stac-browser)

## VEDA backend context

![architecture diagram](.readme/veda-overview-bw.svg)

_Edit this diagram in VS Code using the [Draw.io Integration Extension](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) and export a new SVG_

Veda backend is is the central index of the [VEDA ecosystem](#veda-ecosystem). This project provides the infrastructure for a PgSTAC database, STAC API, and TiTiler. This infrastructure is used to discover, access, and visualize the Analysis Ready Cloud Optimized (ARCO) assets of the VEDA Data Store.

## Deployment

This project uses an AWS CDK [CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) stack to deploy a full AWS virtual private cloud environment with a database and supporting lambda function APIs. The deployment constructs, database, and API services are highly configurable. This section provices basic deployment instructions as well as support for customization.

### Tooling & supporting documentation

- [CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)

### Enviroment variables

An [.example.env](.example.env) template is supplied for local deployments. If updating an existing deployment, it is essential to check the most current values for these variables by fetching these values from AWS Secrets Manager. The environment secrets are named `<app-name>-<stage>-env`, for example `veda-backend-dev-env`.
> **Warning** The environment variables stored as AWS secrets are manually maintained and should be reviewed before deploying updates to existing stacks.

### Fetch environment variables using AWS CLI

To retrieve the variables for a stage that has been previously deployed, the secrets manager can be used to quickly populate an .env file with [scripts/sync-env-local.sh](scripts/sync-env-local.sh).

```bash
./scripts/sync-env-local.sh <app-secret-name>
```

### Basic environment variables

| Name | Explanation |
| --- | --- |
| `APP_NAME` | Optional app name used to name stack and resources, defaults to `veda-backend` |
| `STAGE` | **REQUIRED** Deployment stage used to name stack and resources, i.e. `dev`, `staging`, `prod` |
| `VEDA_DB_PGSTAC_VERSION` | **REQUIRED** version of PgStac database, i.e. 0.7.6 |
| `VEDA_DB_SCHEMA_VERSION` | **REQUIRED** The version of the custom veda-backend schema, i.e. 0.1.1 |
| `VEDA_DB_SNAPSHOT_ID` | **Once used always REQUIRED** Optional RDS snapshot identifier to initialize RDS from a snapshot |

### Advanced configuration

The constructs and applications in this project are configured using pydantic. The settings are defined in config.py files stored alongside the associated construct or application--for example the settings for the RDS PostgreSQL construct are defined in database/infrastructure/config.py. For custom configuration, use environment variables to override the pydantic defaults.

| Construct | Env Prefix | Configuration |
| --- | --- | --- |
| Database | `VEDA_DB` | [database/infrastructure/config.py](database/infrastructure/config.py) |
| Domain | `VEDA_DOMAIN` | [domain/infrastructure/config.py](domain/infrastructure/config.py) |
| Network | `N/A` | [network/infrastructure/config.py](network/infrastructure/config.py) |
| Raster API (TiTiler) | `VEDA_RASTER` | [raster_api/infrastructure/config.py](raster_-_api/infrastructure/config.py) |
| STAC API | `VEDA` | [stac_api/infrastructure/config.py](stac_api/infrastructure/config.py) |
| Routes | `VEDA` | [routes/infrastructure/config.py](routes/infrastructure/config.py) |
| S3 Website | `VEDA` | [s3_website/infrastructure/config.py](s3_website/infrastructure/config.py) |
| App (global settings) | `N/A` | [config.py](config.py) |

### Deploying to the cloud

#### Install deployment pre-requisites

- [Node](https://nodejs.org/)
- [NVM](https://github.com/nvm-sh/nvm#node-version-manager---)
- [jq](https://jqlang.github.io/jq/) (used for exporting environment variable secrets to `.env` in [scripts/sync-env-local.sh](/scripts/sync-env-local.sh))

These can be installed with [homebrew](https://brew.sh/) on MacOS

```bash
brew install node
brew install nvm # Make sure to add nvm to your path
brew install jq
nvm install 20 # .github/workflows/pr.yml uses node version 20
```

#### Virtual environment example

```bash
# `pipes` package required by the `fire` package deprecated in python >3.12
pyenv install 3.12
pyenv shell 3.12
python3 -m venv .venv
source .venv/bin/activate
```

#### Install requirements

```bash
nvm use 20
npm install --location=global aws-cdk
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,deploy,test]"
```

#### Run the deployment

```
# Login to ECR so that you can pull public docker images
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
# Review what infrastructure changes your deployment will cause
cdk diff
# Execute deployment and standby--security changes will require approval for deployment
cdk deploy
```

## Deleting the CloudFormation stack

If this is a development stack that is safe to delete, you can delete the stack in CloudFormation console or via `cdk destroy`, however, the additional manual steps were required to completely delete the stack resources:

1. You will need to disable deletion protection of the RDS database and delete the database.
2. Identify and delete the RDS subnet group associated with the RDS database you just deleted (it will not be automatically removed because of the RDS deletion protection in place when the group was created).
3. If this stack created a new VPC, detach the Internet Gateway (IGW) from the VPC and delete it.
4. If this stack created a new VPC, delete the VPC (this should delete a subnet and security group too).

## Custom deployments

The default settings for this project generate a complete AWS environment including a VPC and gateways for the stack. See this guidance for adjusting the veda-backend stack for existing managed and/or shared AWS environments.

- [Deploy to an existing managed AWS environment](docs/deploying_to_existing_environments.md)
- [Creating a shared base VPC and AWS environment](docs/deploying_to_existing_environments.md#optional-deploy-standalone-base-infrastructure)

## Local Docker deployment

Start up a local stack

```bash
docker compose up
```

Clean up after running locally

```bash
docker compose down
```

## Running tests locally

To run tests implicated in CI, a script is included that requires as little setup as possible

```bash
./scripts/run-local-tests.sh
```

In case of failure, all container logs will be written out to `container_logs.log`.

# Operations

## Adding new data to veda-backend

> **Warning** PgSTAC records should be loaded in the database using [pypgstac](https://github.com/stac-utils/pgstac#pypgstac) for proper indexing and partitioning.

The VEDA ecosystem includes tools specifially created for loading PgSTAC records and optimizing data assets. The [veda-data-airflow](https://github.com/NASA-IMPACT/veda-data-airflow) project provides examples of cloud pipelines that transform data to cloud optimized formats, generate STAC metadata, and submit records for publication to the veda-backend database via veda-backend's ingest API. Veda-backend's integrated ingest system includes an API lambda for enqueuing collection and item records in a DynamoDB table and an ingestor lambda that batch loads DDB enqueued records into the PgSTAC database. Currently, the client id and domain of an existing Cognito user pool programmatic client must be supplied in [configuration](ingest_api/infrastructure/config.py) as `VEDA_CLIENT_ID` and `VEDA_COGNITO_DOMAIN` (the [veda-auth project](https://github.com/NASA-IMPACT/veda-auth) can be used to deploy a Cognito user pool and client). To dispense auth tokens via the ingest API swagger docs and `/token` endpoints, an administrator must add the ingest API lambda URL to the allowed callbacks of the Cognito client.

## Support scripts
Support scripts are provided for manual system operations.

- [Rotate pgstac password](support_scripts/README.md#rotate-pgstac-password)

# VEDA ecosystem

## Projects

| Name | Explanation |
| --- | --- |
| **veda-backend** | Central index (database) and APIs for recording, discovering, viewing, and using VEDA assets |
| [**veda-config**](https://github.com/NASA-IMPACT/veda-config) | Configuration for viewing VEDA assets in dashboard UI  |
| [**veda-ui**](https://github.com/NASA-IMPACT/veda-ui) | Dashboard UI for viewing and analysing VEDA assets |
| [**veda-stac-ingestor**](https://github.com/NASA-IMPACT/veda-stac-ingestor) |  Entry-point for users/services to add new records to database |
| [**veda-data**](https://github.com/NASA-IMPACT/veda-data) | Collection and asset discovery configuration |
| [**veda-data-airflow**](https://github.com/NASA-IMPACT/veda-data-airflow) | Cloud optimize data assets and submit records for publication to veda-stac-ingestor |
| [**veda-docs**](https://github.com/NASA-IMPACT/veda-docs) | Documentation repository for end users of VEDA ecosystem data and tools |
| [**veda-routes**](https://github.com/NASA-IMPACT/veda-routes)| Configuration for VEDA's Content Delivery Network |

## VEDA usage examples

### [VEDA documentation](https://nasa-impact.github.io/veda-docs)

### [VEDA dashboard](https://www.earthdata.nasa.gov/dashboard)

# STAC community resources

## STAC browser

Radiant Earth's [stac-browser](https://github.com/radiantearth/stac-browser) is a browser for STAC catalogs. The demo version of this browser [radiantearth.github.io/stac-browser](https://radiantearth.github.io/stac-browser/#/) can be used to browse the contents of the veda-backend STAC catalog, paste the veda-backend stac-api URL deployed by this project in the demo and click load. Read more about the recent developments and usage of stac-browser [here](https://medium.com/radiant-earth-insights/the-exciting-future-of-the-stac-browser-2351143aa24b).

# License

This project is licensed under **Apache 2**, see the [LICENSE](LICENSE) file for more details.
