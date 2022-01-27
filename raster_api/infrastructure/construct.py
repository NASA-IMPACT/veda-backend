# delta.raster
import os

from aws_cdk import (
    aws_apigatewayv2_alpha,
    aws_apigatewayv2_integrations_alpha,
    aws_ec2,
    aws_iam,
    aws_lambda,
    CfnOutput,
    Duration,
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

        eoraster_function = aws_lambda.Function(
            self,
            f"{id}-raster-lambda",
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
        )

        # # lambda_function.add_environment(key="TITILER_ENDPOINT", value=raster_api.url)
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
        }
        for k, v in db_secrets.items():
            eoraster_function.add_environment(key=k, value=str(v))

        raster_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                "StacApiIntegration", eoraster_function
            )
        )
        self.raster_api = aws_apigatewayv2_alpha.HttpApi(
            self, f"{construct_id}Endpoint", default_integration=raster_api_integration
        )

        print(f"DeltaBackendTilerApi url={self.raster_api.url}")

        CfnOutput(self, "DeltaBackendTilerApi", value=self.raster_api.url)

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
