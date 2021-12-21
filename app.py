#!/usr/bin/env python3
import os

from aws_cdk import (
    App, CfnOutput, Stack, Tags
)
from constructs import Construct

from network.infrastructure.vpc import VpcStack
from database.infrastructure.rds import DatabaseStack

identifier = os.getenv("IDENTIFIER").capitalize()

app = App()

vpc_stack = VpcStack(
    app, 
    f"DeltaVpc{identifier}",
)
database_stack = DatabaseStack(
    app, 
    f"DeltaDatabase{identifier}", 
    vpc_stack.vpc,
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



