#!/usr/bin/env python3
""" CDK Configuration for the delta-backend stack."""

from aws_cdk import App, Aspects, Stack, Tags, aws_iam
from constructs import Construct

from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

from config import PermissionBoundaryAspect, delta_app_settings

# App configuration
# load_dotenv()
# stage = os.environ["STAGE"].lower()
# app_name = "delta-backend"
# vpc_id = os.environ.get("VPC_ID")
# if vpc_id:
#     # If deploying to existing VPC, default stack account and region are required
#     cdk_env = {
#         "account": os.environ["CDK_DEFAULT_ACCOUNT"],
#         "region": os.environ["CDK_DEFAULT_REGION"],
#     }
# else:
#     cdk_env = {}

app = App()


class DeltaStack(Stack):
    """CDK stack for hte delta-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if delta_app_settings.permissions_boundary_policy:
            permission_boundary_policy = aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                delta_app_settings.permissions_boundary_policy,
            )
            aws_iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)


delta_stack = DeltaStack(
    app,
    f"{delta_app_settings.app_name}-{delta_app_settings.stage.lower()}",
    env=delta_app_settings.cdk_env(),
)

if delta_app_settings.vpc_id:
    vpc = VpcConstruct(
        delta_stack,
        "network",
        vpc_id=delta_app_settings.vpc_id,
        stage=delta_app_settings.stage.lower(),
    )
else:
    vpc = VpcConstruct(delta_stack, "network", stage=delta_app_settings.stage.lower())

database = RdsConstruct(
    delta_stack, "database", vpc.vpc, stage=delta_app_settings.stage.lower()
)

domain = DomainConstruct(delta_stack, "domain", stage=delta_app_settings.stage.lower())

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

for key, value in {
    "Project": delta_app_settings.app_name,
    "Stack": delta_app_settings.stage.lower(),
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
