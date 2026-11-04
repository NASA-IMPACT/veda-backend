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
        path_prefix: str | None = None,
        s3_prefix: str | None = None,
        **kwargs,
    ) -> None:

        super().__init__(scope, id, **kwargs)

        website = VedaWebsite(self, "stac-browser-bucket", stage=stage)

        stac_browser_kwargs = {
            "github_repo_tag": version_tag,
            "stac_catalog_url": stac_catalog_url,
            "bucket_arn": website.bucket.bucket_arn,
        }
        if path_prefix:
            stac_browser_kwargs["path_prefix"] = path_prefix

        if s3_prefix:
            stac_browser_kwargs["s3_prefix"] = s3_prefix

        StacBrowser(self, "stac-browser", **stac_browser_kwargs)

        CfnOutput(self, "StacBrowserTag", value=version_tag)
