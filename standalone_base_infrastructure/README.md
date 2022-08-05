# Standalone Base Infrastructure

Optional shared base infrastructure provisioning. This CloudFormation stack is intended to simulate controlled deployment environments. It also useful for deploying a long-standing VPC that can be shared across stacks.

## Deployment

### Fetch environment variables using AWS CLI

To retrieve the variables for a stage that has been previously deployed, the secrets manager can be used to quickly populate an .env file. 
> Note: The environment variables stored as AWS secrets are manually maintained and should be reviewed before using.

```
export AWS_SECRET_ID=<base-name>-env

aws secretsmanager get-secret-value --secret-id ${AWS_SECRET_ID} --query SecretString --output text | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' > .env
```

See main app [deployment instructions](../README.md#deployment).

### Deployment variables

| Name | Explanation |
| --- | --- |
| `BASE_NAME` | App name used to name stack and resources, defaults to `veda-shared` |
| `CDK_DEFAULT_ACCOUNT` | The AWS account id is required to deploy to an exiting VPC |
| `CDK_DEFAULT_REGION` | The AWS region id is required to deploy to an exiting VPC |
| `VPC_CIDR` | The CIDR range to use for the VPC. Default is 10.100.0.0/16 |
| `VPC_MAX_AZS` | Maximum number of availability zones per region. Default is 2. |
| `VPC_NAT_GATEWAYS` | Number of gateways to create. Default is 0. |
