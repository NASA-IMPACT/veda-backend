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
    aws_iam,
    aws_lambda,
    aws_logs,
)
from constructs import Construct

from .config import veda_raster_settings

if typing.TYPE_CHECKING:
    from domain.infrastructure.construct import DomainConstruct


class RasterApiLambdaConstruct(Construct):
    """CDK Construct for a Lambda based TiTiler API with pgstac extension."""

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

        # TODO config
        stack_name = Stack.of(self).stack_name

        veda_raster_function = aws_lambda.Function(
            self,
            "lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="raster_api/runtime/Dockerfile",
                platform="linux/amd64",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            handler="handler.handler",
            memory_size=veda_raster_settings.memory,
            timeout=Duration.seconds(veda_raster_settings.timeout),
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            environment={
                **veda_raster_settings.env,
                "VEDA_RASTER_ENABLE_MOSAIC_SEARCH":str(veda_raster_settings.raster_enable_mosaic_search),
                "VEDA_RASTER_ROOT_PATH":veda_raster_settings.raster_root_path,
                "VEDA_RASTER_STAGE":stage,
                "VEDA_RASTER_PROJECT_NAME":veda_raster_settings.project_name
            },
            tracing=aws_lambda.Tracing.ACTIVE,
        )

        database.pgstac.secret.grant_read(veda_raster_function)
        database.pgstac.connections.allow_from(
            veda_raster_function, port_range=aws_ec2.Port.tcp(5432)
        )

        # Optional AWS S3 requester pays global setting
        if veda_raster_settings.raster_aws_request_payer:
            veda_raster_function.add_environment(
                "AWS_REQUEST_PAYER", veda_raster_settings.raster_aws_request_payer
            )

        integration_kwargs = dict(handler=veda_raster_function)
        if veda_raster_settings.custom_host:
            integration_kwargs[
                "parameter_mapping"
            ] = aws_apigatewayv2_alpha.ParameterMapping().overwrite_header(
                "host",
                aws_apigatewayv2_alpha.MappingValue(veda_raster_settings.custom_host),
            )

        raster_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id,
                **integration_kwargs,
            )
        )

        domain_mapping = None
        # Legacy method to use a custom subdomain for this api (i.e. <stage>-raster.<domain-name>.com)
        # If using a custom root path and/or a proxy server, do not use a custom subdomain
        if domain and domain.raster_domain_name:
            domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
                domain_name=domain.raster_domain_name
            )

        self.raster_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=raster_api_integration,
            default_domain_mapping=domain_mapping,
        )

        CfnOutput(
            self,
            "raster-api",
            value=self.raster_api.url,
            export_name=f"{stack_name}-raster-url",
        )
        CfnOutput(self, "raster-api-arn", value=veda_raster_function.function_arn)

        veda_raster_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::{bucket}/{veda_raster_settings.key}"
                    for bucket in veda_raster_settings.buckets
                ],
            )
        )

        # Optional use sts assume role with GetObject permissions for external S3 bucket(s)
        if veda_raster_settings.raster_data_access_role_arn:
            # Get the role for external data access
            data_access_role = aws_iam.Role.from_role_arn(
                self,
                "data-access-role",
                veda_raster_settings.raster_data_access_role_arn,
            )

            # Allow this lambda to assume the data access role
            data_access_role.grant(
                veda_raster_function.grant_principal,
                "sts:AssumeRole",
            )

            veda_raster_function.add_environment(
                "VEDA_RASTER_DATA_ACCESS_ROLE_ARN",
                veda_raster_settings.raster_data_access_role_arn,
            )

        # Optional configuration to export assume role session into lambda function environment
        if veda_raster_settings.raster_export_assume_role_creds_as_envs:
            veda_raster_function.add_environment(
                "VEDA_RASTER_EXPORT_ASSUME_ROLE_CREDS_AS_ENVS",
                str(veda_raster_settings.raster_export_assume_role_creds_as_envs),
            )
