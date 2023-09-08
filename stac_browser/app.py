#!/usr/bin/env python3
""" CDK Configuration for the browser stack."""


import os

from aws_cdk import App, Stack, Tags
from constructs import Construct

from eoapi_cdk import StacBrowser

app = App()

STAC_API_URL = os.environ["STAC_API_URL"]
STAGE_NAME = os.environ["STAGE"]
APP_NAME = os.environ["APP_NAME"]


class BrowserStack(Stack):
    """CDK stack for the veda STAC browser stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)


browser_stack = BrowserStack(app, f"{APP_NAME}-{STAGE_NAME}")

stac_browser = StacBrowser(
    browser_stack,
    "stac-browser",
    github_repo_tag="v3.1.0",  # hard coded to the latest for now.
    stac_catalog_url=STAC_API_URL,  # using the non-custom-domain for now.
    website_index_document="index.html",  # using simple static website hosting for now without a CloudFront distribution.
)
stac_browser.bucket.grant_public_access()  # make it publicly accessible for the static website hosting to work.

for key, value in {
    "Project": APP_NAME,
    "Stack": STAGE_NAME,
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
