#!/usr/bin/env python3
""" CDK Configuration for the delta-backend stack."""

from aws_cdk import App, Stack, Tags, aws_iam
from constructs import Construct

from config import delta_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

app = App()


class DeltaStack(Stack):
    """CDK stack for hte delta-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if delta_app_settings.permissions_boundary_policy_name:
            permission_boundary_policy = (
                aws_iam.Policy.from_policy_name(
                    self,
                    "permission-boundary",
                    delta_app_settings.permissions_boundary_policy_name,
                )
            )
            aws_iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)


delta_stack = DeltaStack(
    app,
    f"{delta_app_settings.app_name}-{delta_app_settings.stage_name()}",
    env=delta_app_settings.cdk_env(),
)

if delta_app_settings.vpc_id:
    vpc = VpcConstruct(
        delta_stack,
        "network",
        vpc_id=delta_app_settings.vpc_id,
        stage=delta_app_settings.stage_name(),
    )
else:
    vpc = VpcConstruct(delta_stack, "network", stage=delta_app_settings.stage_name())

database = RdsConstruct(
    delta_stack, "database", vpc.vpc, stage=delta_app_settings.stage_name()
)

domain = DomainConstruct(delta_stack, "domain", stage=delta_app_settings.stage_name())

raster_api = RasterApiLambdaConstruct(
    delta_stack,
    "raster-api",
    vpc=vpc.vpc,
    database=database,
    domain_name=domain.raster_domain_name,
)

stac_api = StacApiLambdaConstruct(
    delta_stack,
    "stac-api",
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain_name=domain.stac_domain_name,
)

# TODO this conditional supports deploying a second set of APIs to a separate custom domain and should be removed if no longer necessary
if delta_app_settings.alt_domain():

    alt_domain = DomainConstruct(
        delta_stack,
        "alt-domain",
        stage=delta_app_settings.stage_name(),
        alt_domain=True,
    )

    alt_raster_api = RasterApiLambdaConstruct(
        delta_stack,
        "alt-raster-api",
        vpc=vpc.vpc,
        database=database,
        domain_name=alt_domain.raster_domain_name,
    )

    alt_stac_api = StacApiLambdaConstruct(
        delta_stack,
        "alt-stac-api",
        vpc=vpc.vpc,
        database=database,
        raster_api=raster_api,
        domain_name=alt_domain.stac_domain_name,
    )

for key, value in {
    "Project": delta_app_settings.app_name,
    "Stack": delta_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
