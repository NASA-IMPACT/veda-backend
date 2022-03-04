#!/usr/bin/env python3
from unicodedata import name

from aws_cdk import CfnOutput, aws_ec2
from constructs import Construct


# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/new-vpc-alb-asg-mysql
# https://github.com/aws-samples/aws-cdk-examples/tree/master/python/docker-app-with-asg-alb
class VpcConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        public_subnet = aws_ec2.SubnetConfiguration(
            name="public",
            subnet_type=aws_ec2.SubnetType.PUBLIC,
            cidr_mask=24,
        )
        isolated_subnet = aws_ec2.SubnetConfiguration(
            name="isolated",
            subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=24,
        )

        self.vpc = aws_ec2.Vpc(
            self,
            "vpc",
            max_azs=2,
            cidr="10.10.0.0/16",
            subnet_configuration=[public_subnet, isolated_subnet],
            nat_gateways=0,
        )

        interface_endpoints = [
            (
                "secretsmanager",
                aws_ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            ),
            (
                "cloudwatch-logs",
                aws_ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            ),
        ]
        for (id, service) in interface_endpoints:
            self.vpc.add_interface_endpoint(id, service=service)

        gateway_endpoints = [("s3", aws_ec2.GatewayVpcEndpointAwsService.S3)]
        for (id, service) in gateway_endpoints:
            self.vpc.add_gateway_endpoint(id, service=service)

        CfnOutput(self, "vpc-id", value=self.vpc.vpc_id)
