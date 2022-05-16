# delta-backend
Backend services for the Dashboard Evolution

## Deployment

### Enviroment variables

An [.example.env](.example.env) template is supplied for for local deployments. If updating an existing deployment, it is essential to check the most current values for these variables by fetching these values from AWS Secrets Manager. The environment secrets are named `delta-backend/<stage>-env`, for example the `dev` stack environment variables secret is named `delta-backend/dev-env`.

| Name | Explanation |
| --- | --- |
| `STAGE` | **REQUIRED** Deployment stage used to name stack and resources, i.e. `dev`, `staging`, `prod` |
| `VPC_ID` | Optional resource identifier of VPC, if none a new VPC with public and private subnets will be provisioned. |
| `CDK_DEFAULT_ACCOUNT` | When deploying from a local machine the AWS account id is required to deploy to an exiting VPC |
| `CDK_DEFAULT_REGION` | When deploying from a local machine the AWS region id is required to deploy to an exiting VPC |
| `DELTA_DB_PGSTAC_VERSION` | **REQUIRED** version of PgStac database, i.e. 0.5 |
| `DELTA_DB_SCHEMA_VERSION` | **REQUIRED** The version of the custom delta-backend schema, i.e. 0.1.1 |
| `DELTA_DB_SNAPSHOT_ID` | **Once used always REQUIRED** Optional RDS snapshot identifier to initialize RDS from a snapshot |
| `DELTA_DOMAIN_HOSTED_ZONE_ID` | Optional Route53 zone identifier if using a custom domain name |
| `DELTA_DOMAIN_HOSTED_ZONE_NAME` | Optional custom domain name, i.e. delta-backend.xyz |
| `DELTA_DOMAIN_API_PREFIX` | Optional domain prefix override supports using a custom prefix instead of the STAGE variabe (an alternate version of the stack can be deployed with a unique STAGE=altprod and after testing prod API traffic can be cut over to the alternate version of the stack by setting the prefix to prod) |
| `DELTA_RASTER_ENABLE_MOSAIC_SEARCH` | Optional deploy the raster API with the mosaic/list endpoint TRUE/FALSE |

### CDK context
Currently a named version of the CDK toolkit is used for deployments [`cdk.json`](cdk.json). To use the default CDK toolkit bootstrapped for the account, remove `"@aws-cdk/core:bootstrapQualifier"` from the `"context"` in [`cdk.json`](cdk.json).