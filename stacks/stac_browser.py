from aws_cdk import CfnOutput, Stack
from constructs import Construct
from eoapi_cdk import StacBrowser

from s3_website.infrastructure.construct import VedaWebsite


class StacBrowserStack(Stack):
    """CDK stack for the stac-browser."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        stage: str,
        version_tag: str,
        stac_catalog_url: str,
        **kwargs,
    ) -> None:

        super().__init__(scope, id, **kwargs)

        website = VedaWebsite(self, "stac-browser-bucket", stage=stage)

        StacBrowser(
            self,
            "stac-browser",
            github_repo_tag=version_tag,
            stac_catalog_url=stac_catalog_url,
            bucket_arn=website.bucket.bucket_arn,
        )

        CfnOutput(self, "StacBrowserTag", value=version_tag)
