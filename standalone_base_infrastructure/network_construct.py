"""
CDK construct for standalone base network infrastructure.
"""
from aws_cdk import CfnOutput, aws_ec2
from constructs import Construct
from standalone_config import base_settings


class BaseVpcConstruct(Construct):
    """CDK construct for standalone base infrastructure VPC."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
    ) -> None:
        """Initialized construct."""
        super().__init__(scope, construct_id)

        public_subnet = aws_ec2.SubnetConfiguration(
            name="public",
            subnet_type=aws_ec2.SubnetType.PUBLIC,
        )
        private_subnet = aws_ec2.SubnetConfiguration(
            name="private",
            subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
        )

        nat_gateway_provider = aws_ec2.NatProvider.instance(
            instance_type=aws_ec2.InstanceType("t3.nano")
        )

        vpc = aws_ec2.Vpc(
            self,
            "vpc",
            max_azs=base_settings.vpc_max_azs,
            cidr=base_settings.vpc_cidr,
            subnet_configuration=[public_subnet, private_subnet],
            nat_gateway_provider=nat_gateway_provider,
            nat_gateways=base_settings.vpc_nat_gateways,
        )

        vpc_endpoints = {
            "secretsmanager": aws_ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            "cloudwatch-logs": aws_ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            "s3": aws_ec2.GatewayVpcEndpointAwsService.S3,
            "dynamodb": aws_ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        }

        for (id, service) in vpc_endpoints.items():
            if isinstance(service, aws_ec2.InterfaceVpcEndpointAwsService):
                vpc.add_interface_endpoint(id, service=service)
            elif isinstance(service, aws_ec2.GatewayVpcEndpointAwsService):
                vpc.add_gateway_endpoint(id, service=service)
        
        # TODO the vpc construct should be doing adding private subnet routes for the gateway instance, why isn't it?
        for private_subnet in  vpc.select_subnets(
            subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED
        ).subnets:    
            nat_gateway_provider.configure_subnet(subnet=private_subnet)



        CfnOutput(self, "vpc-id", value=vpc.vpc_id)
