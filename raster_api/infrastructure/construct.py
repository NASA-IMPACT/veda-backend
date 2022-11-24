"""CDK Constrcut for a Lambda based TiTiler API with pgstac extension."""
import os

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

from .config import delta_raster_settings


class RasterApiLambdaConstruct(Construct):
    """CDK Constrcut for a Lambda based TiTiler API with pgstac extension."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc,
        database,
        code_dir: str = "./",
        domain_name: aws_apigatewayv2_alpha.DomainName = None,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        # TODO config
        stack_name = Stack.of(self).stack_name

        delta_raster_function = aws_lambda.Function(
            self,
            "lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(code_dir),
                file="raster_api/runtime/Dockerfile",
                platform="linux/amd64",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            handler="handler.handler",
            memory_size=delta_raster_settings.memory,
            timeout=Duration.seconds(delta_raster_settings.timeout),
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            environment=delta_raster_settings.env or {},
            tracing=aws_lambda.Tracing.ACTIVE
        )

        database.pgstac.secret.grant_read(delta_raster_function)
        database.pgstac.connections.allow_from(
            delta_raster_function, port_range=aws_ec2.Port.tcp(5432)
        )

        delta_raster_function.add_environment(
            "DELTA_RASTER_ENABLE_MOSAIC_SEARCH",
            str(delta_raster_settings.enable_mosaic_search),
        )

        delta_raster_function.add_environment(
            "DELTA_RASTER_PGSTAC_SECRET_ARN", database.pgstac.secret.secret_full_arn
        )

        raster_api_integration = (
            aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
                construct_id, delta_raster_function
            )
        )

        domain_mapping = None
        if domain_name:
            domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
                domain_name=domain_name
            )

        self.raster_api = aws_apigatewayv2_alpha.HttpApi(
            self,
            f"{stack_name}-{construct_id}",
            default_integration=raster_api_integration,
            default_domain_mapping=domain_mapping,
        )

        CfnOutput(self, "raster-api", value=self.raster_api.url)
        CfnOutput(self, "raster-api-arn", value=delta_raster_function.function_arn)

        delta_raster_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::{bucket}/{delta_raster_settings.key}"
                    for bucket in delta_raster_settings.buckets
                ],
            )
        )

        # Optional use sts assume role with GetObject permissions for external S3 bucket(s)
        if delta_raster_settings.data_access_role_arn:
            # Get the role for external data access
            data_access_role = aws_iam.Role.from_role_arn(
                self,
                "data-access-role",
                delta_raster_settings.data_access_role_arn,
            )

            # Allow this lambda to assume the data access role
            data_access_role.grant(
                delta_raster_function.grant_principal,
                "sts:AssumeRole",
            )

            delta_raster_function.add_environment(
                "DELTA_RASTER_DATA_ACCESS_ROLE_ARN",
                delta_raster_settings.data_access_role_arn,
            )
