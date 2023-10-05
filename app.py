#!/usr/bin/env python3
""" CDK Configuration for the veda-backend stack."""

from aws_cdk import App, Stack, Tags, aws_iam
from constructs import Construct

from config import veda_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import ALBConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from routes.infrastructure.construct import CloudfrontDistributionConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

app = App()


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permission_boundary_policy = aws_iam.Policy.from_policy_name(
                self,
                "permission-boundary",
                veda_app_settings.permissions_boundary_policy_name,
            )
            aws_iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)


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


raster_api = RasterApiLambdaConstruct(
    veda_stack,
    "raster-api",
    vpc=vpc.vpc,
    database=database,
    domain_name=None,
)

stac_api = StacApiLambdaConstruct(
    veda_stack,
    "stac-api",
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain_name=None,
)

alb = ALBConstruct(
    veda_stack,
    "alb",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    stac_lambda_function=stac_api.lambda_function,
    raster_lambda_function=raster_api.veda_raster_function,
)

veda_routes = CloudfrontDistributionConstruct(
    veda_stack,
    "routes",
    raster_api_id=alb.lb.load_balancer_dns_name,
    stac_api_id=alb.lb.load_balancer_dns_name,
    region=veda_app_settings.cdk_default_region,
)

# TODO this conditional supports deploying a second set of APIs to a separate custom domain and should be removed if no longer necessary
# if veda_app_settings.alt_domain():
#     alt_domain = DomainConstruct(
#         veda_stack,
#         "alt-domain",
#         stage=veda_app_settings.stage_name(),
#         alt_domain=True,
#     )

#     alt_raster_api = RasterApiLambdaConstruct(
#         veda_stack,
#         "alt-raster-api",
#         vpc=vpc.vpc,
#         database=database,
#         domain_name=alt_domain.raster_domain_name,
#     )

#     alt_stac_api = StacApiLambdaConstruct(
#         veda_stack,
#         "alt-stac-api",
#         vpc=vpc.vpc,
#         database=database,
#         raster_api=raster_api,
#         domain_name=alt_domain.stac_domain_name,
#     )

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
