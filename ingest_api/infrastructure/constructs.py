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
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        lambda_env: Dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = self.build_table()
        self.data_access_role = iam.Role.from_role_arn(
            self, "data-access-role", config.data_access_role
        )

        self.user_pool = cognito.UserPool.from_user_pool_id(
            self, "cognito-user-pool", config.userpool_id
        )

        # create lambda
        self.api_lambda = self.build_api_lambda(
            table=self.table,
            env=lambda_env,
            data_access_role=self.data_access_role,
            user_pool=self.user_pool,
            stage=config.stage,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            db_subnet_public=config.db_subnet_public,
        )

        # create API
        self.api = self.build_api(
            handler=self.api_lambda,
            stage=config.stage,
        )
        self.jwks_url = self.build_jwks_url(config.userpool_id)

        register_ssm_parameter(
            name="jwks_url",
            value=jwks_url,
            description="JWKS URL for Cognito user pool",
        )
        register_ssm_parameter(
            name="dynamodb_table",
            value=table.table_name,
            description="Name of table used to store ingestions",
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
        db_security_group: ec2.ISecurityGroup,
        lambda_env: Dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # continue with ingestor-related methods (build_ingestor, etc.)
        
        self.ingest_lambda = self.build_ingestor(
            table=table,
            env=lambda_env,
            db_secret=db_secret,
            db_vpc=db_vpc,
            db_security_group=db_security_group,
            db_subnet_public=config.db_subnet_public,
            code_dir='/.', # TODO this isn't right
        )

    def build_ingestor(
        self,
        *,
        table: dynamodb.ITable,
        env: Dict[str, str],
        db_secret: secretsmanager.ISecret,
        db_vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        db_subnet_public: bool,
        code_dir: str = "./",
    ) -> aws_lambda.Function:
        handler = aws_lambda.Function(
            self,
            "stac-ingestor",
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="ingest_api/Dockerfile",
                platform="linux/amd64",
            ),
            handler="ingestor.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(180),
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