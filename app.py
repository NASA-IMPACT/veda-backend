#!/usr/bin/env python3
""" CDK Configuration for the veda-backend stack."""

from aws_cdk import App, Aspects, Stack, Tags, aws_iam
from constructs import Construct

from config import veda_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from permissions_boundary.infrastructure.construct import PermissionsBoundaryAspect
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from routes.infrastructure.construct import CloudfrontDistributionConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct
from eoapi_cdk import StacBrowser

app = App()
if veda_app_settings.bootstrap_qualifier:
    app.node.set_context(
        "@aws-cdk/core:bootstrapQualifier", veda_app_settings.bootstrap_qualifier
    )


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permissions_boundary_policy = (
                aws_iam.ManagedPolicy.from_managed_policy_name(
                    self,
                    "permissions-boundary",
                    veda_app_settings.permissions_boundary_policy_name,
                )
            )
            aws_iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)
            Aspects.of(self).add(PermissionsBoundaryAspect(permissions_boundary_policy))


veda_stack = VedaStack(
    app,
    f"{veda_app_settings.app_name}-{veda_app_settings.stage_name()}",
    env=veda_app_settings.cdk_env(),
)

if veda_app_settings.vpc_id:
    vpc = VpcConstruct(
        veda_stack,
        "network",
        vpc_id=veda_app_settings.vpc_id,
        stage=veda_app_settings.stage_name(),
    )
else:
    vpc = VpcConstruct(veda_stack, "network", stage=veda_app_settings.stage_name())

database = RdsConstruct(
    veda_stack, "database", vpc.vpc, stage=veda_app_settings.stage_name()
)

domain = DomainConstruct(veda_stack, "domain", stage=veda_app_settings.stage_name())

raster_api = RasterApiLambdaConstruct(
    veda_stack,
    "raster-api",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    database=database,
    domain=domain,
)

stac_api = StacApiLambdaConstruct(
    veda_stack,
    "stac-api",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain=domain,
)

veda_routes = CloudfrontDistributionConstruct(
    veda_stack,
    "routes",
    stage=veda_app_settings.stage_name(),
    raster_api_id=raster_api.raster_api.api_id,
    stac_api_id=stac_api.stac_api.api_id,
    region=veda_app_settings.cdk_default_region,
)

# eoapi-cdk stac-browser only supported for stacks with cloudfront distribution
if veda_app_settings.cloudfront:
    stac_browser = StacBrowser(
        veda_stack,
        "stac-browser",
        github_repo_tag=veda_app_settings.stac_browser_tag,
        stac_catalog_url=veda_routes.stac_catalog_url,
        bucket_arn=veda_routes.bucket.bucket_arn,
    )

# TODO this conditional supports deploying a second set of APIs to a separate custom domain and should be removed if no longer necessary
if veda_app_settings.alt_domain():
    alt_domain = DomainConstruct(
        veda_stack,
        "alt-domain",
        stage=veda_app_settings.stage_name(),
        alt_domain=True,
    )

    alt_raster_api = RasterApiLambdaConstruct(
        veda_stack,
        "alt-raster-api",
        stage=veda_app_settings.stage_name(),
        vpc=vpc.vpc,
        database=database,
        domain_name=alt_domain.raster_domain_name,
    )

    alt_stac_api = StacApiLambdaConstruct(
        veda_stack,
        "alt-stac-api",
        stage=veda_app_settings.stage_name(),
        vpc=vpc.vpc,
        database=database,
        raster_api=raster_api,
        domain_name=alt_domain.stac_domain_name,
    )

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
