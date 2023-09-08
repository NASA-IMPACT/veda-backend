#!/usr/bin/env python3
""" CDK Configuration for the browser stack."""


import os

from aws_cdk import App, RemovalPolicy, Stack, Tags
from aws_cdk import aws_s3 as s3
from constructs import Construct

from eoapi_cdk import StacBrowser

app = App()

STAC_API_URL = os.environ["STAC_API_URL"]
STAGE_NAME = os.environ["STAGE_NAME"]
APP_NAME = os.environ["APP_NAME"]


class BrowserStack(Stack):
    """CDK stack for the veda STAC browser stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)


browser_stack = BrowserStack(app, f"{APP_NAME}-{STAGE_NAME}")

stac_browser_bucket = s3.Bucket(
    browser_stack,
    "stac-browser-bucket",
    bucket_name=f"{APP_NAME}-{STAGE_NAME}",
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

stac_browser = StacBrowser(
    browser_stack,
    "stac-browser",
    github_repo_tag="v3.1.0",  # hard coded to the latest for now.
    stac_catalog_url=STAC_API_URL,  # using the non-custom-domain for now.
    bucket_arn=stac_browser_bucket.bucket_arn,
)

for key, value in {
    "Project": APP_NAME,
    "Stack": STAGE_NAME,
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
