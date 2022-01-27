#!/usr/bin/env python3
import os

from aws_cdk import App, Stack, Tags
from constructs import Construct

from network.infrastructure.vpc import VpcConstruct
from database.infrastructure.rds import RdsConstruct
from stac_api.infrastructure.lambda_function import StacApiLambdaConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct

identifier = os.getenv("IDENTIFIER").capitalize()

app = App()


class DeltaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


delta_stack = DeltaStack(app, f"DeltaBackend{identifier}")

vpc = VpcConstruct(delta_stack, f"Vpc{identifier}")

database = RdsConstruct(delta_stack, f"Database{identifier}", vpc.vpc)


raster_api = RasterApiLambdaConstruct(
    delta_stack, f"DeltaBackendRasterApi{identifier}", vpc=vpc.vpc, database=database
)

stac_api = StacApiLambdaConstruct(
    delta_stack,
    f"DeltaBackendStacApi{identifier}",
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
)

app.synth()

for key, value in {
    "Project": "delta-backend",
    "Stack": identifier,
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)
