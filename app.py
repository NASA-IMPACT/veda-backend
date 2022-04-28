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
    cdk_env = {
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    }
except KeyError:
    vpc_id = None
    cdk_env = {}

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

if vpc_id:
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

for key, value in {
    "Project": app_name,
    "Stack": stage,
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
