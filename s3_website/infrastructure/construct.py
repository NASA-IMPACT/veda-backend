"""CDK Construct for getting or creating S3 static website for both a stac-browser and for optional cloudfront origin."""
from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import veda_s3_website_settings


class VedaWebsite(Construct):
    """CDK Construct for a S3 website"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        stack_name = Stack.of(self).stack_name.split("-")[0]

        if veda_s3_website_settings.stac_browser_bucket:
            self.bucket = s3.Bucket.from_bucket_name(
                self,
                construct_id,
                bucket_name=veda_s3_website_settings.stac_browser_bucket,
            )
        else:
            self.bucket = s3.Bucket(
                self,
                construct_id,
                bucket_name=f"{stack_name}-{stage}-stac-browser",
                removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True,
                website_index_document="index.html",
                public_read_access=True,
                block_public_access=s3.BlockPublicAccess(
                    block_public_acls=False,
                    block_public_policy=False,
                    ignore_public_acls=False,
                    restrict_public_buckets=False,
                ),
                object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            )

        CfnOutput(
            self,
            "bucket-website",
            value=f"https://{self.bucket.bucket_website_domain_name}",
            key="stacbrowserurl",
        )
