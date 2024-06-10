import os
import typing
from typing import Dict, Optional, Union

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_apigatewayv2_alpha, aws_apigatewayv2_integrations_alpha
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import aws_lambda_event_sources as events
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from .config import IngestorConfig

if typing.TYPE_CHECKING:
    from domain.infrastructure.construct import DomainConstruct


class ApiConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: IngestorConfig,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_vpc_subnets=ec2.SubnetSelection,
        domain: Optional["DomainConstruct"] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = self.build_table()
        self.user_pool = cognito.UserPool.from_user_pool_id(
            self, "cognito-user-pool", config.userpool_id
        )
        self.jwks_url = self.build_jwks_url(config.userpool_id)
        db_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "db-security-group",
            security_group_id=config.stac_db_security_group_id,
        )

        lambda_env = {
            "DYNAMODB_TABLE": self.table.table_name,
            "JWKS_URL": self.jwks_url,
            "NO_PYDANTIC_SSM_SETTINGS": "1",
            "STAC_URL": config.stac_api_url,
            "USERPOOL_ID": config.userpool_id,
            "CLIENT_ID": config.client_id,
            "CLIENT_SECRET": config.client_secret,
            "RASTER_URL": config.raster_api_url,
            "ROOT_PATH": config.ingest_root_path,
            "STAGE": config.stage,
            "COGNITO_DOMAIN": config.cognito_domain,
        }

        build_api_lambda_params = {
            "table": self.table,
            "user_pool": self.user_pool,
            "db_secret": db_secret,
            "db_vpc": db_vpc,
            "db_security_group": db_security_group,
        }

        if config.raster_data_access_role_arn:
            lambda_env["DATA_ACCESS_ROLE_ARN"] = config.raster_data_access_role_arn
            build_api_lambda_params["data_access_role"] = iam.Role.from_role_arn(
                self, "data-access-role", config.raster_data_access_role_arn
            )

        if config.raster_aws_request_payer:
            lambda_env["AWS_REQUEST_PAYER"] = config.raster_aws_request_payer

        build_api_lambda_params["env"] = lambda_env

        # create lambda
        self.api_lambda = self.build_api_lambda(**build_api_lambda_params)
        self.api_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::{bucket}/{config.key}" for bucket in config.buckets
                ],
            )
        )

        # create API
        self.api: aws_apigatewayv2_alpha.HttpApi = self.build_api(
            construct_id=construct_id,
            handler=self.api_lambda,
            domain=domain,
            custom_host=config.custom_host,
        )

        # CfnOutput(self, "ingest-api", value=self.api.url)
        stack_name = Stack.of(self).stack_name
        CfnOutput(
            self,
            "stac-ingestor-api-url",
            export_name=f"{stack_name}-stac-ingestor-api-url",
            value=self.api.url,
        )

        register_ssm_parameter(
            self,
            name="jwks_url",
            value=self.jwks_url,
            description="JWKS URL for Cognito user pool",
        )
        register_ssm_parameter(
            self,
            name="dynamodb_table",
            value=self.table.table_name,
            description="Name of table used to store ingestions",
        )

    def build_api_lambda(
        self,
        *,
        table: dynamodb.ITable,
        env: Dict[str, str],
        user_pool: cognito.IUserPool,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        data_access_role: Union[iam.IRole, None] = None,
        code_dir: str = "./",
    ) -> apigateway.LambdaRestApi:
        stack_name = Stack.of(self).stack_name
        handler_role = iam.Role(
            self,
            "execution-role",
            description=(
                "Role used by STAC Ingestor. Manually defined so that we can choose a "
                "name that is supported by the data access roles trust policy"
            ),
            role_name=f"stac-ingestion-api-{stack_name}-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            ],
        )

        handler = aws_lambda.Function(
            self,
            "api-handler",
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="ingest_api/runtime/Dockerfile",
                platform="linux/amd64",
            ),
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(30),
            handler="handler.handler",
            role=handler_role,
            environment={"DB_SECRET_ARN": db_secret.secret_arn, **env},
            vpc=db_vpc,
            memory_size=2048,
            log_format="JSON",
        )
        table.grant_read_write_data(handler)
        if data_access_role:
            data_access_role.grant(
                handler.grant_principal,
                "sts:AssumeRole",
            )

        handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:AdminInitiateAuth"],
                resources=[user_pool.user_pool_arn],
            )
        )

        # Allow handler to read DB secret
        db_secret.grant_read(handler)

        # Allow handler to connect to DB
        db_security_group.add_ingress_rule(
            peer=handler.connections.security_groups[0],
            connection=ec2.Port.tcp(5432),
            description="Allow connections from STAC Ingestor",
        )
        return handler

    def build_api(
        self,
        *,
        construct_id: str,
        handler: aws_lambda.IFunction,
        domain,
        custom_host: Optional[str],
    ) -> aws_apigatewayv2_alpha.HttpApi:
        integration_kwargs = dict(handler=handler)
        if custom_host:
            integration_kwargs[
                "parameter_mapping"
            ] = aws_apigatewayv2_alpha.ParameterMapping().overwrite_header(
                "host",
                aws_apigatewayv2_alpha.MappingValue(custom_host),
            )

        ingest_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id,
                **integration_kwargs,
            )
        )

        domain_mapping = None
        # Legacy method to use a custom subdomain for this api (i.e. <stage>-ingest.<domain-name>.com)
        # If using a custom root path and/or a proxy server, do not use a custom subdomain
        if domain and domain.ingest_domain_name:
            domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
                domain_name=domain.ingest_domain_name
            )
        stack_name = Stack.of(self).stack_name

        return aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=ingest_api_integration,
            default_domain_mapping=domain_mapping,
        )

    def build_jwks_url(self, userpool_id: str) -> str:
        region = userpool_id.split("_")[0]
        return (
            f"https://cognito-idp.{region}.amazonaws.com"
            f"/{userpool_id}/.well-known/jwks.json"
        )

    # item ingest table, comsumed by ingestor
    def build_table(self) -> dynamodb.ITable:
        table = dynamodb.Table(
            self,
            "ingestions-table",
            partition_key={"name": "created_by", "type": dynamodb.AttributeType.STRING},
            sort_key={"name": "id", "type": dynamodb.AttributeType.STRING},
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            stream=dynamodb.StreamViewType.NEW_IMAGE,
        )
        table.add_global_secondary_index(
            index_name="status",
            partition_key={"name": "status", "type": dynamodb.AttributeType.STRING},
            sort_key={"name": "created_at", "type": dynamodb.AttributeType.STRING},
        )
        return table


class IngestorConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: IngestorConfig,
        table: dynamodb.ITable,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_vpc_subnets=ec2.SubnetSelection,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # continue with ingestor-related methods (build_ingestor, etc.)
        lambda_env = {
            "DYNAMODB_TABLE": table.table_name,
            "NO_PYDANTIC_SSM_SETTINGS": "1",
            "STAC_URL": config.stac_api_url,
            "USERPOOL_ID": config.userpool_id,
            "CLIENT_ID": config.client_id,
            "CLIENT_SECRET": config.client_secret,
            "RASTER_URL": config.raster_api_url,
        }

        if config.raster_data_access_role_arn:
            lambda_env["DATA_ACCESS_ROLE_ARN"] = config.raster_data_access_role_arn

        db_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "db-security-group",
            security_group_id=config.stac_db_security_group_id,
        )

        self.ingest_lambda = self.build_ingestor(
            table=table,
            env=lambda_env,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            db_vpc_subnets=db_vpc_subnets,
        )

    def build_ingestor(
        self,
        *,
        table: dynamodb.ITable,
        env: Dict[str, str],
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        db_vpc_subnets: ec2.SubnetSelection,
        code_dir: str = "./",
    ) -> aws_lambda.Function:
        handler = aws_lambda.Function(
            self,
            "stac-ingestor",
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="ingest_api/runtime/Dockerfile",
                platform="linux/amd64",
            ),
            handler="ingestor.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(180),
            environment={"DB_SECRET_ARN": db_secret.secret_arn, **env},
            vpc=db_vpc,
            vpc_subnets=db_vpc_subnets,
            allow_public_subnet=True,
            memory_size=2048,
        )

        # Allow handler to read DB secret
        db_secret.grant_read(handler)

        # Allow handler to connect to DB
        db_security_group.add_ingress_rule(
            peer=handler.connections.security_groups[0],
            connection=ec2.Port.tcp(5432),
            description="Allow connections from STAC Ingestor",
        )

        # Allow handler to write results back to DBƒ
        table.grant_write_data(handler)

        # Trigger handler from writes to DynamoDB table
        handler.add_event_source(
            events.DynamoEventSource(
                table=table,
                # Read when batches reach size...
                batch_size=1000,
                # ... or when window is reached.
                max_batching_window=Duration.seconds(10),
                # Read oldest data first.
                starting_position=aws_lambda.StartingPosition.TRIM_HORIZON,
                retry_attempts=1,
            )
        )

        return handler


def register_ssm_parameter(
    ctx: Construct,  # context for param init
    name: str,
    value: str,
    description: str,
) -> ssm.IStringParameter:
    parameter_namespace = Stack.of(ctx).stack_name
    return ssm.StringParameter(
        ctx,
        f"{name.replace('_', '-')}-parameter",
        description=description,
        parameter_name=f"/{parameter_namespace}/{name}",
        string_value=value,
    )


def get_db_secret(
    ctx: Construct, secret_name: str, stage: str
) -> secretsmanager.ISecret:
    return secretsmanager.Secret.from_secret_name_v2(
        ctx, f"pgstac-db-secret-{stage}", secret_name
    )
