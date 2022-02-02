# delta.raster
import os

from aws_cdk import (
    aws_apigatewayv2_alpha,
    aws_apigatewayv2_integrations_alpha,
    aws_ec2,
    aws_iam,
    aws_lambda,
    aws_logs,
    CfnOutput,
    Duration,
    Stack,
)
from constructs import Construct
from .config import eoraster_settings


class RasterApiLambdaConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc,
        database,
        code_dir: str = "./",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id)

        # TODO config
        stack_name = Stack.of(self).stack_name

        eoraster_function = aws_lambda.Function(
            self,
            f"lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="raster_api/runtime/Dockerfile",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            handler="handler.handler",
            memory_size=1536,  # TODO: from config
            timeout=Duration.minutes(2),  # TODO: from config
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
        )

        database.pgstac.secret.grant_read(eoraster_function)
        database.pgstac.connections.allow_from(
            eoraster_function, port_range=aws_ec2.Port.tcp(5432)
        )

        db_secrets = {
            "POSTGRES_HOST_READER": database.pgstac.secret.secret_value_from_json(
                "host"
            ).to_string(),
            "POSTGRES_HOST_WRITER": database.pgstac.secret.secret_value_from_json(
                "host"
            ).to_string(),
            "POSTGRES_DBNAME": database.pgstac.secret.secret_value_from_json(
                "dbname"
            ).to_string(),
            "POSTGRES_USER": database.pgstac.secret.secret_value_from_json(
                "username"
            ).to_string(),
            "POSTGRES_PASS": database.pgstac.secret.secret_value_from_json(
                "password"
            ).to_string(),
            "POSTGRES_PORT": database.pgstac.secret.secret_value_from_json(
                "port"
            ).to_string(),
            "POSTGRES_HOST": database.pgstac.secret.secret_value_from_json(
                "host"
            ).to_string(),
        }
        for k, v in db_secrets.items():
            eoraster_function.add_environment(key=k, value=str(v))

        raster_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id, eoraster_function
            )
        )
        self.raster_api = aws_apigatewayv2_alpha.HttpApi(
            self, f"{stack_name}-{construct_id}", default_integration=raster_api_integration
        )

        print(f"raster-api url={self.raster_api.url}")

        CfnOutput(self, "raster-api", value=self.raster_api.url)

        for k, v in db_secrets.items():
            eoraster_function.add_environment(key=k, value=str(v))

        eoraster_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::{bucket}/{eoraster_settings.key}"
                    for bucket in eoraster_settings.buckets
                ],
            )
        )

        database.pgstac.connections.allow_from(
            eoraster_function, port_range=aws_ec2.Port.tcp(5432)
        )
