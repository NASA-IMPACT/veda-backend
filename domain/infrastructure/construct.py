#!/usr/bin/env python3
from aws_cdk import (CfnOutput, aws_apigatewayv2_alpha, aws_certificatemanager,
                     aws_route53, aws_route53_targets)
from constructs import Construct

from .config import delta_domain_settings


# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/new-vpc-alb-asg-mysql
# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/docker-app-with-asg-alb
class DomainConstruct(Construct):
    def __init__(
        self, scope: Construct, construct_id: str, stage: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stac_domain_name = None
        self.raster_domain_name = None

        if (
            delta_domain_settings.hosted_zone_id
            and delta_domain_settings.hosted_zone_name
        ):

            hosted_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
                self,
                "hosted-zone",
                hosted_zone_id=delta_domain_settings.hosted_zone_id,
                zone_name=delta_domain_settings.hosted_zone_name,
            )
            certificate = aws_certificatemanager.Certificate(
                self,
                "certificate",
                domain_name="*.delta-backend.xyz",
                validation=aws_certificatemanager.CertificateValidation.from_dns(
                    hosted_zone=hosted_zone
                ),
            )
            self.raster_domain_name = aws_apigatewayv2_alpha.DomainName(
                self,
                "raster-api-custom-domain",
                domain_name=f"{stage.lower()}-raster.delta-backend.xyz",
                # domain_name=f"{stage.lower()}-raster",
                certificate=certificate,
            )

            aws_route53.ARecord(
                self,
                "raster-api-dns-record",
                zone=hosted_zone,
                target=aws_route53.RecordTarget.from_alias(
                    aws_route53_targets.ApiGatewayv2DomainProperties(
                        regional_domain_name=self.raster_domain_name.regional_domain_name,
                        regional_hosted_zone_id=self.raster_domain_name.regional_hosted_zone_id,
                    )
                ),
                record_name=self.raster_domain_name.name,
            )

            self.stac_domain_name = aws_apigatewayv2_alpha.DomainName(
                self,
                "stac-api-custom-domain",
                domain_name=f"{stage.lower()}-stac.delta-backend.xyz",
                # domain_name=f"{stage.lower()-stac"
                certificate=certificate,
            )

            aws_route53.ARecord(
                self,
                "stac-api-dns-record",
                zone=hosted_zone,
                target=aws_route53.RecordTarget.from_alias(
                    aws_route53_targets.ApiGatewayv2DomainProperties(
                        regional_domain_name=self.stac_domain_name.regional_domain_name,
                        regional_hosted_zone_id=self.stac_domain_name.regional_hosted_zone_id,
                    )
                ),
                record_name=self.stac_domain_name.name,
            )

        CfnOutput(self, "hosted-zone-name", value=hosted_zone.zone_name)