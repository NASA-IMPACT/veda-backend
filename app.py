#!/usr/bin/env python3
""" CDK Configuration for the delta-backend stack."""
import os

from aws_cdk import App, Stack, Tags
from constructs import Construct
from dotenv import load_dotenv

from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

# App configuration
load_dotenv()
stage = os.environ["STAGE"].lower()
app_name = "delta-backend"
try:
    vpc_id = os.environ["VPC_ID"]
    existing_vpc = True
    # If deploying to existing VPC, default stack account and region are required
    cdk_env = {
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    }
except KeyError:
    existing_vpc = False
    cdk_env = {}

# TODO remove temporary alternative domain variables or move to app settings configuration
alt_domain = all(
    [
        os.environ.get("DELTA_DOMAIN_ALT_HOSTED_ZONE_ID"),
        os.environ.get("DELTA_DOMAIN_ALT_HOSTED_ZONE_NAME"),
    ]
)

app = App()


class DeltaStack(Stack):
    """CDK stack for hte delta-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)


delta_stack = DeltaStack(
    app,
    f"{app_name}-{stage}",
    env=cdk_env,
)

if existing_vpc:
    vpc = VpcConstruct(delta_stack, "network", vpc_id=vpc_id, stage=stage)
else:
    vpc = VpcConstruct(delta_stack, "network", stage=stage)

database = RdsConstruct(delta_stack, "database", vpc.vpc, stage=stage)

domain = DomainConstruct(delta_stack, "domain", stage=stage)

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
if alt_domain:
    alt_domain = DomainConstruct(
        delta_stack, "alt-domain", stage=stage, alt_domain=True
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
    "Project": app_name,
    "Stack": stage,
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
