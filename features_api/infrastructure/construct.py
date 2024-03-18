import json
import os
from typing import Any, Dict, List, Optional

import aws_cdk.aws_logs as logs
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as apigw_integrations
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import core

from config import APISettings, DBSettings

api_settings = APISettings()
db_settings = DBSettings()


class BootstrappedDb(core.Construct):
    """
    Given an RDS database, connect to DB and create a database, user, and
    password
    """

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        db: rds.DatabaseInstance,
        new_dbname: str,
        new_username: str,
        secrets_prefix: str,
    ) -> None:
        """Update RDS database."""
        super().__init__(scope, id)

        # TODO: Utilize a singleton function.
        handler = aws_lambda.Function(
            self,
            "DatabaseBootstrapper",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"),
                file="stack/Dockerfile.db",
                platform="linux/amd64",
            ),
            timeout=core.Duration.minutes(5),
            vpc=db.vpc,
            allow_public_subnet=True,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        self.secret = secretsmanager.Secret(
            self,
            id,
            secret_name=os.path.join(
                secrets_prefix, id.replace(" ", "_"), self.node.unique_id[-8:]
            ),
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "dbname": new_dbname,
                        "engine": "postgres",
                        "port": 5432,
                        "host": db.instance_endpoint.hostname,
                        "username": new_username,
                    },
                ),
                generate_string_key="password",
                exclude_punctuation=True,
            ),
            description=f"Deployed by {core.Stack.of(self).stack_name}",
        )

        self.resource = core.CustomResource(
            scope=scope,
            id="BootstrappedDbResource",
            service_token=handler.function_arn,
            properties={
                "conn_secret_arn": db.secret.secret_arn,
                "new_user_secret_arn": self.secret.secret_arn,
            },
            # We do not need to run the custom resource on STAC Delete
            # Custom Resource are not physical resources so it's OK to `Retain` it
            removal_policy=core.RemovalPolicy.RETAIN,
        )

        # Allow lambda to...
        # read new user secret
        self.secret.grant_read(handler)
        # read database secret
        db.secret.grant_read(handler)
        # connect to database
        db.connections.allow_from(handler, port_range=ec2.Port.tcp(5432))

    def is_required_by(self, construct: core.Construct):
        """Register required services."""
        return construct.node.add_dependency(self.resource)


class LambdaStack(core.Stack):
    """Lambda Stack"""

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        stage: str,
        name: str,
        code_dir: str = "./",
        **kwargs: Any,
    ) -> None:
        """Define stack."""
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, f"{id}-vpc", nat_gateways=0)

        interface_endpoints = [
            (
                "SecretsManager Endpoint",
                ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            ),
            (
                "CloudWatch Logs Endpoint",
                ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            ),
        ]
        for (key, service) in interface_endpoints:
            vpc.add_interface_endpoint(key, service=service)

        gateway_endpoints = [("S3", ec2.GatewayVpcEndpointAwsService.S3)]
        for (key, service) in gateway_endpoints:
            vpc.add_gateway_endpoint(key, service=service)

        db = rds.DatabaseInstance(
            self,
            f"{id}-postgres-db",
            vpc=vpc,
            engine=rds.DatabaseInstanceEngine.POSTGRES,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
            ),
            database_name=db_settings.dbname,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            backup_retention=core.Duration.days(7),
            deletion_protection=api_settings.stage.lower() == "production",
            removal_policy=core.RemovalPolicy.SNAPSHOT
            if api_settings.stage.lower() == "production"
            else core.RemovalPolicy.DESTROY,
        )

        setup_db = BootstrappedDb(
            self,
            "Features DB for EIS Fires",
            db=db,
            new_dbname=db_settings.dbname,
            new_username=db_settings.user,
            secrets_prefix=os.path.join(stage, name),
        )

        core.CfnOutput(
            self,
            f"{id}-database-secret-arn",
            value=db.secret.secret_arn,
            description="Arn of the SecretsManager instance holding the connection info for Postgres DB",
        )

        db_secrets = {
            "POSTGRES_HOST": setup_db.secret.secret_value_from_json(
                "host"
            ).to_string(),
            "POSTGRES_DBNAME": setup_db.secret.secret_value_from_json(
                "dbname"
            ).to_string(),
            "POSTGRES_USER": setup_db.secret.secret_value_from_json(
                "username"
            ).to_string(),
            "POSTGRES_PASS": setup_db.secret.secret_value_from_json(
                "password"
            ).to_string(),
            "POSTGRES_PORT": setup_db.secret.secret_value_from_json(
                "port"
            ).to_string(),
        }

        env = {}
        env["DB_MIN_CONN_SIZE"] = "1"
        env["DB_MAX_CONN_SIZE"] = "1"

        api_function = aws_lambda.Function(
            self,
            f"{id}-vector-lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="stack/Dockerfile.lambda",
                platform="linux/amd64",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            handler="handler.handler",
            memory_size=api_settings.memory,
            timeout=core.Duration.seconds(api_settings.timeout),
            environment=env,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        for k, v in db_secrets.items():
            api_function.add_environment(key=k, value=str(v))

        db.connections.allow_from(api_function, port_range=ec2.Port.tcp(5432))

        api = apigw.HttpApi(
            self,
            f"{id}-endpoint",
            default_integration=apigw_integrations.HttpLambdaIntegration(
                f"{id}-integration",
                handler=api_function,
            ),
        )
        core.CfnOutput(self, "lambda", value=api.url.strip("/"))

        setup_db.is_required_by(api_function)