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
        vpc,
        database,
        raster_api,  # TODO: typing!
        code_dir: str = "./",
        domain_name: aws_apigatewayv2_alpha.DomainName = None,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        # TODO config
        stack_name = Stack.of(self).stack_name

        lambda_function = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="stac_api/runtime/Dockerfile",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            memory_size=veda_stac_settings.memory,
            timeout=Duration.seconds(veda_stac_settings.timeout),
            environment={
                "DB_MIN_CONN_SIZE": "0",
                "DB_MAX_CONN_SIZE": "1",
                **{k.upper(): v for k, v in veda_stac_settings.env.items()},
            },
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            tracing=aws_lambda.Tracing.ACTIVE,
        )

        # # lambda_function.add_environment(key="TITILER_ENDPOINT", value=raster_api.url)
        database.pgstac.secret.grant_read(lambda_function)
        database.pgstac.connections.allow_from(
            lambda_function, port_range=aws_ec2.Port.tcp(5432)
        )

        lambda_function.add_environment("TITILER_ENDPOINT", raster_api.raster_api.url)

        lambda_function.add_environment(
            "VEDA_STAC_PGSTAC_SECRET_ARN", database.pgstac.secret.secret_full_arn
        )

        lambda_function.add_environment(
            "VEDA_STAC_PATH_PREFIX", veda_stac_settings.stac_path_prefix
        )

        stac_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id,
                handler=lambda_function,
                parameter_mapping=(
                    aws_apigatewayv2_alpha.ParameterMapping().overwrite_header(
                        "host",
                        aws_apigatewayv2_alpha.MappingValue(
                            veda_stac_settings.domain_hosted_zone_name
                        )
                        if veda_stac_settings.domain_hosted_zone_name
                        else None,
                    )
                ),
            )
        )

        domain_mapping = None
        if domain_name:
            domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
                domain_name=domain_name
            )

        self.stac_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=stac_api_integration,
            default_domain_mapping=domain_mapping,
        )

        CfnOutput(self, "stac-api", value=self.stac_api.url)
