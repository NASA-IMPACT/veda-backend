"""CDK Construct for a Cloudfront Distribution."""
from typing import Optional
from urllib.parse import urlparse

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_certificatemanager as certificatemanager
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53, aws_route53_targets
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import veda_route_settings


class CloudfrontDistributionConstruct(Construct):
    """CDK Construct for a Cloudfront Distribution."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        raster_api_id: str,
        stac_api_id: str,
        region: Optional[str],
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        stack_name = Stack.of(self).stack_name

        if veda_route_settings.cloudfront:
            s3Bucket = s3.Bucket.from_bucket_name(
                self,
                "stac-browser-bucket",
                bucket_name=veda_route_settings.stac_browser_bucket,
            )

            # Certificate must be in zone us-east-1
            domain_cert = (
                certificatemanager.Certificate.from_certificate_arn(
                    self, "domainCert", veda_route_settings.cert_arn
                )
                if veda_route_settings.cert_arn
                else None
            )

            self.distribution = cf.Distribution(
                self,
                stack_name,
                comment=stack_name,
                default_behavior=cf.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        s3Bucket.bucket_website_domain_name,
                        protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                        origin_id="stac-browser",
                    ),
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                ),
                certificate=domain_cert,
                domain_names=[f"{stage}.{veda_route_settings.domain_hosted_zone_name}"]
                if veda_route_settings.domain_hosted_zone_name
                else None,
                additional_behaviors={
                    "/api/stac*": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            f"{stac_api_id}.execute-api.{region}.amazonaws.com",
                            origin_id="stac-api",
                        ),
                        cache_policy=cf.CachePolicy.CACHING_DISABLED,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                        origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    ),
                    "/api/raster*": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            f"{raster_api_id}.execute-api.{region}.amazonaws.com",
                            origin_id="raster-api",
                        ),
                        cache_policy=cf.CachePolicy.CACHING_DISABLED,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                        origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    ),
                    "/api/ingest**": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            urlparse(veda_route_settings.ingest_url).hostname,
                            origin_id="ingest-api",
                            origin_path="/dev",
                        ),
                        cache_policy=cf.CachePolicy.CACHING_DISABLED,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    ),
                },
            )

            hosted_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
                self,
                "hosted-zone",
                hosted_zone_id=veda_route_settings.domain_hosted_zone_id,
                zone_name=veda_route_settings.domain_hosted_zone_name,
            )

            aws_route53.ARecord(
                self,
                "cloudfront-dns-record",
                zone=hosted_zone,
                target=aws_route53.RecordTarget.from_alias(
                    aws_route53_targets.CloudFrontTarget(self.distribution)
                ),
                record_name=stage,
            )

            CfnOutput(self, "Endpoint", value=self.distribution.domain_name)
