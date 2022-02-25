import os

from aws_cdk import (CfnOutput, Duration, Stack, aws_apigatewayv2_alpha,
                     aws_apigatewayv2_integrations_alpha, aws_ec2, aws_lambda,
                     aws_logs)
from constructs import Construct

from .config import delta_stac_settings


class StacApiLambdaConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc,
        database,
        raster_api,  # TODO: typing!
        code_dir: str = "./",
        domain_name: aws_apigatewayv2_alpha.DomainName = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id)

        # TODO config
        stack_name = Stack.of(self).stack_name

        lambda_function = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="stac_api/runtime/Dockerfile",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            memory_size=delta_stac_settings.memory,
            timeout=Duration.seconds(delta_stac_settings.timeout),
            environment=delta_stac_settings.env or {},
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
        )

        # # lambda_function.add_environment(key="TITILER_ENDPOINT", value=raster_api.url)
        database.pgstac.secret.grant_read(lambda_function)
        database.pgstac.connections.allow_from(
            lambda_function, port_range=aws_ec2.Port.tcp(5432)
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
            lambda_function.add_environment(key=k, value=str(v))

        lambda_function.add_environment("TITILER_ENDPOINT", raster_api.raster_api.url)

        stac_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id, handler=lambda_function
            )
        )
        domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
            domain_name=domain_name
        )
        stac_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=stac_api_integration,
            default_domain_mapping=domain_mapping,
        )

        print(f"stac-api url={stac_api.url}")

        CfnOutput(self, "stac-api", value=stac_api.url)
