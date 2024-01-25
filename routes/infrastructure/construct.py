"""CDK Construct for a Cloudfront Distribution."""
from typing import Optional

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_certificatemanager as certificatemanager
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
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
        origin_bucket: s3.Bucket,
        region: Optional[str],
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        stack_name = Stack.of(self).stack_name

        if veda_route_settings.cloudfront:

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
                        origin_bucket.bucket_website_domain_name,
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
                },
            )

            self.hosted_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
                self,
                "hosted-zone",
                hosted_zone_id=veda_route_settings.domain_hosted_zone_id,
                zone_name=veda_route_settings.domain_hosted_zone_name,
            )

            # Infer cloudfront arn to add to bucket resource policy
            self.distribution_arn = f"arn:aws:cloudfront::{self.distribution.env.account}:distribution/{self.distribution.distribution_id}"
            origin_bucket.add_to_resource_policy(
                permission=iam.PolicyStatement(
                    actions=["s3:GetObject"],
                    conditions={
                        "StringEquals": {"aws:SourceArn": self.distribution_arn}
                    },
                    effect=iam.Effect("ALLOW"),
                    principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                    resources=[origin_bucket.arn_for_objects("*")],
                    sid="AllowCloudFrontServicePrincipal",
                )
            )

            CfnOutput(self, "Endpoint", value=self.distribution.domain_name)

    def add_ingest_behavior(
        self,
        ingest_api,
        stage: str,
        region: Optional[str] = "us-west-2",
    ):
        """Required as second step as ingest API depends on stac API route"""
        if veda_route_settings.cloudfront:
            self.distribution.add_behavior(
                "/api/ingest*",
                origin=origins.HttpOrigin(
                    f"{ingest_api.api_id}.execute-api.{region}.amazonaws.com",
                    origin_id="ingest-api",
                ),
                cache_policy=cf.CachePolicy.CACHING_DISABLED,
                allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            )
            self.distribution.add_behavior(
                "/api/workflows*",
                origin=origins.HttpOrigin(
                    f"{ingest_api.api_id}.execute-api.{region}.amazonaws.com",
                    origin_id="workflow-api",
                ),
                cache_policy=cf.CachePolicy.CACHING_DISABLED,
                allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            )

    def create_route_records(self, stage: str):
        """This is a seperate function so that it can be called after all behaviors are instantiated"""
        if veda_route_settings.cloudfront:
            aws_route53.ARecord(
                self,
                "cloudfront-dns-record",
                zone=self.hosted_zone,
                target=aws_route53.RecordTarget.from_alias(
                    aws_route53_targets.CloudFrontTarget(self.distribution)
                ),
                record_name=stage,
            )
