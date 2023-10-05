"""CDK Construct for a custom API domain."""
from typing import Optional

from aws_cdk import (
    CfnOutput,
    aws_apigatewayv2_alpha,
    aws_route53 as route53,
    aws_certificatemanager as certificatemanager,
    aws_route53_targets as route53_targets,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct

from .config import veda_domain_settings


class ALBConstruct(Construct):
    """CDK Construct for a custom API domain."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        vpc,
        stac_lambda_function,
        raster_lambda_function,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "hosted-zone",
            hosted_zone_id=veda_domain_settings.domain_hosted_zone_id,
            zone_name=veda_domain_settings.domain_hosted_zone_name,
        )
        certificate = certificatemanager.Certificate(
            self,
            "certificate",
            domain_name=f"*.{veda_domain_settings.domain_hosted_zone_name}",
            validation=certificatemanager.CertificateValidation.from_dns(
                hosted_zone=hosted_zone
            ),
        )

        self.lb = elbv2.ApplicationLoadBalancer(
            self, "application load balancer", vpc=vpc, internet_facing=True
        )

        target_group_stac = elbv2.ApplicationTargetGroup(
            self,
            "target-group-stac",
            target_group_name=f"target-veda-stac-{stage}",
            vpc=vpc,
            targets=[elbv2_targets.LambdaTarget(stac_lambda_function)],
        )

        target_group_raster = elbv2.ApplicationTargetGroup(
            self,
            "target-group-raster",
            target_group_name=f"target-veda-raster-{stage}",
            vpc=vpc,
            targets=[elbv2_targets.LambdaTarget(raster_lambda_function)],
        )

        listenerHTTPS = self.lb.add_listener(
            "Listener",
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=404,
                content_type="text/plain",
                message_body="Cannot route your request;",
            ),
            port=80,
        )

        listenerHTTPS.add_target_groups(
            "raster-target",
            target_groups=[target_group_raster],
            conditions=[
                elbv2.ListenerCondition.path_patterns(
                    [f"{veda_domain_settings.raster_path_prefix}*"]
                )
            ],
            priority=200,
        )

        listenerHTTPS.add_target_groups(
            "stac-target",
            target_groups=[target_group_stac],
            conditions=[
                elbv2.ListenerCondition.path_patterns(
                    [f"{veda_domain_settings.stac_path_prefix}*"]
                )
            ],
            priority=202,
        )

        # route53.ARecord(self, "stac-dns-record",
        #     zone=zone,
        #     target=route53.RecordTarget.from_alias(
        #         route53_targets.LoadBalancerTarget(self.lb)
        #     ),
        #     record_name="stac"
        # )

        CfnOutput(self, "stac-api", value=self.lb.load_balancer_dns_name)

        # self.stac_domain_name = None
        # self.raster_domain_name = None

        # if (
        #     veda_domain_settings.hosted_zone_id
        #     and veda_domain_settings.hosted_zone_name
        # ):
        #     # If alternative custom domain provided, use it instead of the default
        #     if alt_domain is True:
        #         hosted_zone_name = veda_domain_settings.alt_hosted_zone_name
        #         hosted_zone_id = veda_domain_settings.alt_hosted_zone_id
        #     else:
        #         hosted_zone_name = veda_domain_settings.hosted_zone_name
        #         hosted_zone_id = veda_domain_settings.hosted_zone_id

        #     hosted_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
        #         self,
        #         "hosted-zone",
        #         hosted_zone_id=hosted_zone_id,
        #         zone_name=hosted_zone_name,
        #     )
        #     certificate = aws_certificatemanager.Certificate(
        #         self,
        #         "certificate",
        #         domain_name=f"*.{hosted_zone_name}",
        #         validation=aws_certificatemanager.CertificateValidation.from_dns(
        #             hosted_zone=hosted_zone
        #         ),
        #     )

        #     # Use custom api prefix if provided or deployment stage if not
        #     if veda_domain_settings.api_prefix:
        #         raster_url_prefix = f"{veda_domain_settings.api_prefix.lower()}-raster"
        #         stac_url_prefix = f"{veda_domain_settings.api_prefix.lower()}-stac"
        #     else:
        #         raster_url_prefix = f"{stage.lower()}-raster"
        #         stac_url_prefix = f"{stage.lower()}-stac"
        #     raster_domain_name = f"{raster_url_prefix}.{hosted_zone_name}"
        #     stac_domain_name = f"{stac_url_prefix}.{hosted_zone_name}"

        #     self.raster_domain_name = aws_apigatewayv2_alpha.DomainName(
        #         self,
        #         "rasterApiCustomDomain",
        #         domain_name=raster_domain_name,
        #         certificate=certificate,
        #     )

        #     aws_route53.ARecord(
        #         self,
        #         "raster-api-dns-record",
        #         zone=hosted_zone,
        #         target=aws_route53.RecordTarget.from_alias(
        #             aws_route53_targets.ApiGatewayv2DomainProperties(
        #                 regional_domain_name=self.raster_domain_name.regional_domain_name,
        #                 regional_hosted_zone_id=self.raster_domain_name.regional_hosted_zone_id,
        #             )
        #         ),
        #         # Note: CDK will append the hosted zone name (eg: `veda-backend.xyz` to this record name)
        #         record_name=raster_url_prefix,
        #     )

        #     self.stac_domain_name = aws_apigatewayv2_alpha.DomainName(
        #         self,
        #         "stacApiCustomDomain",
        #         domain_name=stac_domain_name,
        #         certificate=certificate,
        #     )

        #     aws_route53.ARecord(
        #         self,
        #         "stac-api-dns-record",
        #         zone=hosted_zone,
        #         target=aws_route53.RecordTarget.from_alias(
        #             aws_route53_targets.ApiGatewayv2DomainProperties(
        #                 regional_domain_name=self.stac_domain_name.regional_domain_name,
        #                 regional_hosted_zone_id=self.stac_domain_name.regional_hosted_zone_id,
        #             )
        #         ),
        #         # Note: CDK will append the hosted zone name (eg: `veda-backend.xyz` to this record name)
        #         record_name=stac_url_prefix,
        #     )

        #     CfnOutput(
        #         self,
        #         "raster-api",
        #         value=f"https://{raster_url_prefix}.{hosted_zone_name}/docs",
        #     )
        #     CfnOutput(
        #         self, "stac-api", value=f"https://{stac_url_prefix}.{hosted_zone_name}/"
        #     )
