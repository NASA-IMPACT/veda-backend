import os
from typing import Dict

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigateway
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


class ApiConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: IngestorConfig,
        stac_url: str,
        raster_url: str,
        table: dynamodb.ITable,
        jwks_url: str,
        data_access_role: iam.IRole,
        user_pool: cognito.IUserPool,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        lambda_env: Dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create lambda
        self.api_lambda = self.build_api_lambda(
            table=table,
            env=lambda_env,
            data_access_role=data_access_role,
            user_pool=user_pool,
            stage=config.stage,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            db_subnet_public=config.db_subnet_public,
        )

        # create API
        self.api = self.build_api(
            handler=api_lambda,
            stage=config.stage,
        )

    def build_api_lambda(
        self,
        *,
        table: dynamodb.ITable,
        env: Dict[str, str],
        data_access_role: iam.IRole,
        user_pool: cognito.IUserPool,
        stage: str,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        db_subnet_public: bool,
        code_dir: str = "./",
    ) -> apigateway.LambdaRestApi:
        handler_role = iam.Role(
            self,
            "execution-role",
            description=(
                "Role used by STAC Ingestor. Manually defined so that we can choose a "
                "name that is supported by the data access roles trust policy"
            ),
            role_name=f"delta-backend-staging-stac-ingestion-api-{stage}",
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
                file="ingest_api/Dockerfile",
                platform="linux/amd64",
            ),
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(30),
            handler="handler.handler",
            role=handler_role,
            environment={"DB_SECRET_ARN": db_secret.secret_arn, **env},
            vpc=db_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
                if db_subnet_public
                else ec2.SubnetType.PRIVATE_ISOLATED
            ),
            allow_public_subnet=True,
            memory_size=2048,
        )
        table.grant_read_write_data(handler)
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
        handler: aws_lambda.IFunction,
        stage: str,
    ) -> apigateway.LambdaRestApi:
        return apigateway.LambdaRestApi(
            self,
            f"{Stack.of(self).stack_name}-api",
            handler=handler,
            cloud_watch_role=True,
            deploy_options=apigateway.StageOptions(stage_name=stage),
        )

        


class IngestorConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: IngestorConfig,
        table: dynamodb.ITable,
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        lambda_env: Dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # continue with ingestor-related methods (build_ingestor, etc.)
        # ...


class StacIngestionApi(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: IngestorConfig,
        stac_url: str,
        raster_url: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # setup shared resources like table, jwks_url, data_access_role, user_pool, env, db_secret, db_vpc, db_security_group
        # ...

        # Instantiate the constructs
        api = ApiConstruct(
            self,
            "ApiConstruct",
            config=config,
            stac_url=stac_url,
            raster_url=raster_url,
            table=table,
            jwks_url=jwks_url,
            data_access_role=data_access_role,
            user_pool=user_pool,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            lambda_env=lambda_env,
        )

        ingestor = IngestorConstruct(
            self,
            "IngestorConstruct",
            config=config,
            table=table,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            lambda_env=lambda_env,
        )

        self.jwks_param = register_ssm_parameter(
            self,
            "jwks-url",
            jwks_url,
            "URL of the JWKS endpoint for the user pool",
        )

        self.dynamo_param = register_ssm_parameter(
            self,
            "dynamo-table",
            table.table_name,
            "Name of the DynamoDB table",
        )


def register_ssm_parameter(
        ctx: Construct, # context for param init
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

def get_db_secret(ctx: Construct, secret_name: str, stage: str) -> secretsmanager.ISecret:
        return secretsmanager.Secret.from_secret_name_v2(
            ctx, f"pgstac-db-secret-{stage}", secret_name
        )