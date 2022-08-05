#!/usr/bin/env python3
""" CDK Configuration for the delta-backend stack."""

from aws_cdk import App, Stack, Tags, aws_iam
from constructs import Construct

from config import base_settings
from network_construct import BaseVpcConstruct

app = App()

class BaseStack(Stack):
    """CDK stack for base infrastructure"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

base_stack = BaseStack(
    app,
    base_settings.base_name,
    env=base_settings.cdk_env(),
    tags={
        "Project": base_settings.base_name,
        "Stack": base_settings.base_name,
        "Client": "nasa-impact",
        "Owner": "ds",
    }
)

vpc = BaseVpcConstruct(base_stack, "network")

app.synth()
