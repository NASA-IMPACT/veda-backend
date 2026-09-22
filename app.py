#!/usr/bin/env python3
"""CDK Configuration for the veda-backend stack."""

import subprocess

from aws_cdk import App, Tags

from config import veda_app_settings
from stacks.stac_browser import StacBrowserStack
from stacks.veda_backend import VedaStack

app = App()
if veda_app_settings.bootstrap_qualifier:
    app.node.set_context(
        "@aws-cdk/core:bootstrapQualifier", veda_app_settings.bootstrap_qualifier
    )

git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
try:
    git_tag = subprocess.check_output(["git", "describe", "--tags"]).decode().strip()
except subprocess.CalledProcessError:
    git_tag = "no-tag"

veda_stack = VedaStack(
    app,
    veda_app_settings.veda_backend_stack_name,
    env=veda_app_settings.cdk_env(),
    git_sha=git_sha,
    stage=veda_app_settings.stage,
    vpc_id=veda_app_settings.vpc_id,
    subnet_ids=veda_app_settings.subnet_ids,
    permissions_boundary_policy_name=veda_app_settings.permissions_boundary_policy_name,
)

if veda_app_settings.stac_catalog_url:
    stac_browser = StacBrowserStack(
        app,
        veda_app_settings.stac_browser_stack_name,
        stage=veda_app_settings.stage,
        version_tag=veda_app_settings.stac_browser_tag,
        stac_catalog_url=veda_app_settings.stac_catalog_url,
    )

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage,
    "Client": "nasa-impact",
    "Owner": veda_app_settings.owner,
    "GitCommit": git_sha,
    "GitTag": git_tag,
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
