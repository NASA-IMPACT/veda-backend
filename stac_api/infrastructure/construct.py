"""CDK Construct for a Lambda backed API implementing stac-fastapi."""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_apigatewayv2_alpha,
    aws_apigatewayv2_integrations_alpha,
    aws_ec2,
    aws_lambda,
    aws_logs,
)
from constructs import Construct

from .config import veda_stac_settings


class StacApiLambdaConstruct(Construct):
    """CDK Construct for a Lambda backed API implementing stac-fastapi."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        vpc,
        database,
        raster_api,  # TODO: typing!
        code_dir: str = "./",
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        # TODO config
        stack_name = Stack.of(self).stack_name

        lambda_env = {
            "VEDA_STAC_PROJECT_NAME": veda_stac_settings.project_name,
            "VEDA_STAC_PROJECT_DESCRIPTION": veda_stac_settings.project_description,
            "VEDA_STAC_ROOT_PATH": veda_stac_settings.stac_root_path,
            "VEDA_STAC_STAGE": stage,
            "VEDA_STAC_ENABLE_TRANSACTIONS": str(
                veda_stac_settings.stac_enable_transactions
            ),
            "DB_MIN_CONN_SIZE": "0",
            "DB_MAX_CONN_SIZE": "1",
            **{k.upper(): v for k, v in veda_stac_settings.env.items()},
        }

        if veda_stac_settings.keycloak_stac_api_client_id is not None:
            lambda_env[
                "VEDA_STAC_CLIENT_ID"
            ] = veda_stac_settings.keycloak_stac_api_client_id
        if veda_stac_settings.openid_configuration_url is not None:
            lambda_env["VEDA_STAC_OPENID_CONFIGURATION_URL"] = str(
                veda_stac_settings.openid_configuration_url
            )

        lambda_function = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="stac_api/runtime/Dockerfile",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            memory_size=veda_stac_settings.memory,
            timeout=Duration.seconds(veda_stac_settings.timeout),
            environment=lambda_env,
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            tracing=aws_lambda.Tracing.ACTIVE,
        )

        # # lambda_function.add_environment(key="TITILER_ENDPOINT", value=raster_api.url)
        database.pgstac.secret.grant_read(lambda_function)
        database.pgstac.connections.allow_from(
            lambda_function, port_range=aws_ec2.Port.tcp(5432)
        )

        if veda_stac_settings.custom_host:
            titler_endpoint = f"https://{veda_stac_settings.custom_host}{veda_stac_settings.raster_root_path}/"
        else:
            titler_endpoint = raster_api.raster_api.url
        lambda_function.add_environment("TITILER_ENDPOINT", titler_endpoint)

        lambda_function.add_environment(
            "VEDA_STAC_PGSTAC_SECRET_ARN", database.pgstac.secret.secret_full_arn
        )

        integration_kwargs = dict(handler=lambda_function)
        if veda_stac_settings.custom_host:
            integration_kwargs[
                "parameter_mapping"
            ] = aws_apigatewayv2_alpha.ParameterMapping().overwrite_header(
                "host",
                aws_apigatewayv2_alpha.MappingValue(veda_stac_settings.custom_host),
            )
        stac_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id,
                **integration_kwargs,
            )
        )

        self.stac_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=stac_api_integration,
            disable_execute_api_endpoint=veda_stac_settings.disable_default_apigw_endpoint,
        )

        CfnOutput(
            self,
            "stac-api",
            value=self.stac_api.url,
            export_name=f"{stack_name}-stac-url",
            key="stacapiurl",
        )
