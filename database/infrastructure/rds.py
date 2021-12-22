from aws_cdk import (
    aws_ec2,
    aws_rds,
    CfnOutput, Stack, RemovalPolicy
)
from constructs import Construct

from database.infrastructure.custom_resource.bootstrapper import BootstrapPgStac


# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
# https://github.com/NASA-IMPACT/hls-sentinel2-downloader-serverless/blob/main/cdk/downloader_stack.py
# https://github.com/aws-samples/aws-cdk-examples/blob/master/python/new-vpc-alb-asg-mysql/cdk_vpc_ec2/cdk_rds_stack.py
class RdsConstruct(Construct):

    def __init__(
        self, 
        scope: Construct,
        construct_id: str, 
        vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Provision RDS Resource
        database = aws_rds.DatabaseInstance(
            self,
            construct_id,
            vpc=vpc,
            engine=aws_rds.DatabaseInstanceEngine.POSTGRES,
            instance_type=aws_ec2.InstanceType.of(
                aws_ec2.InstanceClass.BURSTABLE3, 
                aws_ec2.InstanceSize.SMALL
            ),
            vpc_subnets=aws_ec2.SubnetSelection(
                subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED
            ),
            deletion_protection=False, # TODO we do want deletion protection
            removal_policy=RemovalPolicy.DESTROY, # TODO we need a safe removal policy like snapshot
        )

        # Use custom resource to bootstrap PgSTAC database
        BootstrapPgStac(
            self,
            "BootstrappedPgStac",
            database=database,
            new_dbname="postgis", # TODO this is config!
            new_username="delta", # TODO this is config!
            secrets_prefix=Stack.of(self).stack_name # TODO
        )

        CfnOutput(
            self,
            "SecretArn",
            value=database.secret.secret_arn,
            description=f"Arn of the Secrets Manager instance holding the connection info for the {construct_id} postgres database"
        )

        
