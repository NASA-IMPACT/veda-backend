"""CDK Construct for a custom API domain (under the route 53 domain: delta-backend.xyz)."""
from aws_cdk import (
    CfnOutput,
    aws_apigatewayv2_alpha,
    aws_certificatemanager,
    aws_route53,
    aws_route53_targets,
)
from constructs import Construct

from .config import delta_domain_settings


class DomainConstruct(Construct):
    """CDK Construct for a custom API domain (under the route 53 domain: delta-backend.xyz)."""

    def __init__(
        self, scope: Construct, construct_id: str, stage: str, **kwargs
    ) -> None:
        """."""
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

            # Use custom api prefix if provided or deployment stage if not
            if delta_domain_settings.api_prefix:
                raster_url_prefix = f"{delta_domain_settings.api_prefix.lower()}-raster"
                stac_url_prefix = f"{delta_domain_settings.api_prefix.lower()}-stac"
            else:
                raster_url_prefix = f"{stage.lower()}-raster"
                stac_url_prefix = f"{stage.lower()}-stac"
            raster_domain_name = f"{raster_url_prefix}.delta-backend.xyz"
            stac_domain_name = f"{stac_url_prefix}.delta-backend.xyz"

            self.raster_domain_name = aws_apigatewayv2_alpha.DomainName(
                self,
                "rasterApiCustomDomain",
                domain_name=raster_domain_name,
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
                # Note: CDK will append the hosted zone name (eg: `delta-backend.xyz` to this record name)
                record_name=raster_url_prefix,
            )

            self.stac_domain_name = aws_apigatewayv2_alpha.DomainName(
                self,
                "stacApiCustomDomain",
                domain_name=stac_domain_name,
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
                # Note: CDK will append the hosted zone name (eg: `delta-backend.xyz` to this record name)
                record_name=stac_url_prefix,
            )

            CfnOutput(
                self,
                "raster-api",
                value=f"https://{raster_url_prefix}.delta-backend.xyz/docs",
            )
            CfnOutput(
                self, "stac-api", value=f"https://{stac_url_prefix}.delta-backend.xyz/"
            )
