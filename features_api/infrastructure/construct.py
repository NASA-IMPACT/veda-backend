"""CDK Constrcut for a Lambda based TiTiler API with pgstac extension."""
import os
import typing
from typing import Optional

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

from .config import features_lambda_settings

if typing.TYPE_CHECKING:
    from domain.infrastructure.construct import DomainConstruct


class FeaturesAPILambdaConstruct(Construct):
    """Features Construct"""
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        vpc,
        database,
        code_dir: str = "./",
        # domain_name: aws_apigatewayv2_alpha.DomainName = None,
        domain: Optional["DomainConstruct"] = None,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        stack_name = Stack.of(self).stack_name

        features_api_function = aws_lambda.Function(
            self,
            "lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="features_api/runtime/Dockerfile",
                platform="linux/amd64",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            handler="handler.handler",
            memory_size=features_lambda_settings.features_memory,
            timeout=Duration.seconds(features_lambda_settings.features_timeout),
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            environment=features_lambda_settings.env or {},
            tracing=aws_lambda.Tracing.ACTIVE,
        )

        database.postgis.secret.grant_read(features_api_function)
        database.postgis.connections.allow_from(
            features_api_function, port_range=aws_ec2.Port.tcp(5432)
        )

        features_api_function.add_environment(
            "VEDA_FEATURES_POSTGIS_SECRET_ARN", database.postgis.secret.secret_full_arn
        )

        features_api_function.add_environment(
            "VEDA_FEATURES_ROOT_PATH", features_lambda_settings.features_root_path
        )

        integration_kwargs = dict(handler=features_api_function)
        if features_lambda_settings.custom_host:
            integration_kwargs[
                "parameter_mapping"
            ] = aws_apigatewayv2_alpha.ParameterMapping().overwrite_header(
                "host",
                aws_apigatewayv2_alpha.MappingValue(
                    features_lambda_settings.custom_host
                ),
            )

        features_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id,
                **integration_kwargs,
            )
        )

        domain_mapping = None
        # Legacy method to use a custom subdomain for this api (i.e. <stage>-features.<domain-name>.com)
        # If using a custom root path and/or a proxy server, do not use a custom subdomain
        if domain and domain.features_domain_name:
            domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
                domain_name=domain.features_domain_name
            )

        self.features_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=features_api_integration,
            default_domain_mapping=domain_mapping,
        )

        CfnOutput(
            self,
            "features-api",
            value=self.features_api.url,
            export_name=f"{stack_name}-features-url",
        )
        CfnOutput(self, "features-api-arn", value=features_api_function.function_arn)
