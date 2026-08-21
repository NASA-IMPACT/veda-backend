"""
CDK construct for veda-backend VPC.
"""

from aws_cdk import CfnOutput, Stack
from aws_cdk.aws_ec2 import (
    GatewayVpcEndpointAwsService,
    InterfaceVpcEndpointAwsService,
    SubnetConfiguration,
    SubnetType,
    Vpc,
)
from constructs import Construct

from .config import (
    BaseVpcSettings,
    dev_vpc_settings,
    prod_vpc_settings,
    staging_vpc_settings,
)


# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/new-vpc-alb-asg-mysql
# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/docker-app-with-asg-alb
class VpcConstruct(Construct):
    """CDK construct for veda-backend VPC."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        vpc_id: str | None = None,
    ) -> None:
        """Initialized construct."""
        super().__init__(scope, construct_id)
        stack_name = Stack.of(self).stack_name

        # Get existing VPC if provided
        if vpc_id:
            self.vpc = Vpc.from_lookup(
                self,
                "vpc",
                vpc_id=vpc_id,
            )
        # Or create a new VPC using the deployment stage configuration
        else:
            veda_vpc_settings: BaseVpcSettings
            # Union of pydantic base settings is unpredictable
            # so set stage settings conditionally
            if stage == "prod":
                veda_vpc_settings = prod_vpc_settings
            elif stage == "staging":
                veda_vpc_settings = staging_vpc_settings
            else:
                veda_vpc_settings = dev_vpc_settings

            public_subnet = SubnetConfiguration(
                name="public",
                subnet_type=SubnetType.PUBLIC,
                cidr_mask=veda_vpc_settings.public_mask,
            )
            private_subnet = SubnetConfiguration(
                name="private",
                subnet_type=SubnetType.PRIVATE_WITH_EGRESS,
                cidr_mask=veda_vpc_settings.private_mask,
            )

            self.vpc = Vpc(
                self,
                "vpc",
                max_azs=veda_vpc_settings.max_azs,
                cidr=veda_vpc_settings.cidr,
                subnet_configuration=[public_subnet, private_subnet],
                nat_gateways=veda_vpc_settings.nat_gateways,
            )

            vpc_endpoints = {
                "secretsmanager": InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
                "cloudwatch-logs": InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
                "s3": GatewayVpcEndpointAwsService.S3,
                "dynamodb": GatewayVpcEndpointAwsService.DYNAMODB,
                "ecr": InterfaceVpcEndpointAwsService.ECR,
                "ecr-docker": InterfaceVpcEndpointAwsService.ECR_DOCKER,
                "sts": InterfaceVpcEndpointAwsService.STS,
            }

            for id, service in vpc_endpoints.items():
                if isinstance(service, InterfaceVpcEndpointAwsService):
                    self.vpc.add_interface_endpoint(id, service=service)
                elif isinstance(service, GatewayVpcEndpointAwsService):
                    self.vpc.add_gateway_endpoint(id, service=service)

        CfnOutput(
            self,
            "vpc-id",
            value=self.vpc.vpc_id,
            export_name=f"{stack_name}-stac-db-vpc-id",
        )
