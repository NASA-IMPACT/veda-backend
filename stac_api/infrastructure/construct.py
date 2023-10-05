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
    aws_route53 as route53,
    aws_certificatemanager as certificatemanager,
    aws_route53_targets as route53_targets,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
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

        self.lambda_function = aws_lambda.Function(
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
        database.pgstac.secret.grant_read(self.lambda_function)
        database.pgstac.connections.allow_from(
            self.lambda_function, port_range=aws_ec2.Port.tcp(5432)
        )

        self.lambda_function.add_environment(
            "TITILER_ENDPOINT", raster_api.raster_api.url
        )

        self.lambda_function.add_environment(
            "VEDA_STAC_PGSTAC_SECRET_ARN", database.pgstac.secret.secret_full_arn
        )

        self.lambda_function.add_environment(
            "VEDA_STAC_PATH_PREFIX", veda_stac_settings.path_prefix
        )

        # zone = route53.HostedZone.from_hosted_zone_attributes(
        #         self,
        #         "hosted-zone",
        #         hosted_zone_id="Z061650539BO6YWF9XDMA",
        #         zone_name="delta-backend.xyz",
        #     )

        # domain_cert = certificatemanager.Certificate.from_certificate_arn(
        #     self,
        #     "domainCert", "arn:aws:acm:us-west-2:853558080719:certificate/012bf180-dc4c-4dee-9cba-d3eb64607e13")

        # self.lb = elbv2.ApplicationLoadBalancer(self, "LB",
        #         vpc=vpc,
        #         internet_facing=True
        #     )

        # target_group = elbv2.ApplicationTargetGroup(
        #     self,
        #     "target-group",
        #     target_group_name="target-veda-stac-dev",
        #     vpc=vpc,
        #     targets=[elbv2_targets.LambdaTarget(lambda_function)],
        # )

        # listenerHTTPS = self.lb.add_listener(
        #     "Listener",
        #     port=80,
        #     default_target_groups=[target_group]
        #     )

        # listenerHTTPS.add_targets("STAC Function",
        #     port=8080,
        #     targets=[lambda_function]
        # )

        # listenerHTTPS.add_targets("STAC lambda Function",
        #     targets=[elbv2_targets.LambdaTarget(lambda_function)]
        #     )

        # listenerHTTPS.add_target_groups(
        #     "target",
        #     target_groups=[target_group],
        #     conditions=[elbv2.ListenerCondition.path_patterns([f"{veda_stac_settings.path_prefix}*"])],
        #     priority=202,
        # )

        # self.lb.add_redirect()

        # route53.ARecord(self, "stac-dns-record",
        #     zone=zone,
        #     target=route53.RecordTarget.from_alias(
        #         route53_targets.LoadBalancerTarget(self.lb)
        #     ),
        #     record_name="stac"
        # )

        # stac_api_integration = (
        #     aws_apigatewayv2_integrations_alpha.HttpLambdaIntegration(
        #         construct_id, handler=lambda_function
        #     )
        # )

        # domain_mapping = None
        # if domain_name:
        #     domain_mapping = aws_apigatewayv2_alpha.DomainMappingOptions(
        #         domain_name=domain_name
        #     )

        # self.stac_api = aws_apigatewayv2_alpha.HttpApi(
        #     self,
        #     f"{stack_name}-{construct_id}",
        #     default_integration=stac_api_integration,
        #     default_domain_mapping=domain_mapping,
        # )

        # CfnOutput(self, "stac-api", value=self.lb.load_balancer_dns_name)
