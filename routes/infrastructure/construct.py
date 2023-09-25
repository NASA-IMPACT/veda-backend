"""CDK Construct for a Cloudfront Distribution."""
from typing import Optional
from urllib.parse import urlparse

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_certificatemanager as certificatemanager
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import veda_route_settings


class CloudfrontDistributionConstruct(Construct):
    """CDK Construct for a Cloudfront Distribution."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
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

            no_cache_policy = cf.CachePolicy(
                self,
                "no-cache-policy",
                default_ttl=Duration.seconds(0),
                min_ttl=Duration.seconds(0),
                max_ttl=Duration.seconds(0),
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
                    ),
                    cache_policy=no_cache_policy,
                ),
                certificate=domain_cert,
                domain_names=[veda_route_settings.domain_hosted_zone_name]
                if veda_route_settings.domain_hosted_zone_name
                else None,
                additional_behaviors={
                    "/api/stac*": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            f"{stac_api_id}.execute-api.{region}.amazonaws.com"
                        ),
                        cache_policy=no_cache_policy,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    ),
                    "/api/raster*": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            f"{raster_api_id}.execute-api.{region}.amazonaws.com"
                        ),
                        cache_policy=no_cache_policy,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    ),
                    "/api/ingest*": cf.BehaviorOptions(
                        origin=origins.HttpOrigin(
                            urlparse(veda_route_settings.ingest_url).hostname
                        ),
                        cache_policy=no_cache_policy,
                        allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    ),
                },
            )

        CfnOutput(self, "Endpoint", value=self.distribution.domain_name)
