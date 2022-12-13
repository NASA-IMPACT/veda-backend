# Advanced Configuration
The constructs and applications in this project are configured using [pydantic](https://docs.pydantic.dev/usage/settings/). The settings are defined in config.py files stored alongside the associated construct or application--for example the settings for the RDS PostgreSQL construct are defined in [database/infrastructure/config.py](../database/infrastructure/config.py); the settings for the TiTiler API are defined in [raster_api/runtime/src/config.py](../raster_api/runtime/src/config.py). For custom configuration, use environment variables to override the pydantic defaults. 

## Selected configuration variables
Environment variables for specific VEDA backend components are prefixed, for example database configuration variables are prefixed `VEDA_DB`. See the config.py file in each construct for the appropriate prefix.
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