from aws_cdk import (
    aws_ec2,
    aws_rds,
    CfnOutput, RemovalPolicy, Stack
)
from constructs import Construct

from database.infrastructure.custom_resource.construct import BootstrapPgStac


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

        # TODO config
        stack_name = Stack.of(self).stack_name

        # Provision RDS Resource
        database = aws_rds.DatabaseInstance(
            self,
            id="rds",
            instance_identifier=f"{stack_name}-postgres",
            vpc=vpc,
            engine=aws_rds.DatabaseInstanceEngine.POSTGRES,
            instance_type=aws_ec2.InstanceType.of(
                aws_ec2.InstanceClass.BURSTABLE3, 
                aws_ec2.InstanceSize.SMALL
            ),
            vpc_subnets=aws_ec2.SubnetSelection(
                subnet_type=aws_ec2.SubnetType.PUBLIC
            ),
            deletion_protection=False, # TODO we do want deletion protection
            removal_policy=RemovalPolicy.DESTROY, # TODO we need a safe removal policy like snapshot
            publicly_accessible=True,
        )

        # Use custom resource to bootstrap PgSTAC database
        self.pgstac = BootstrapPgStac(
            self,
            "pgstac",
            database=database,
            new_dbname="postgis", # TODO this is config!
            new_username="delta", # TODO this is config!
            secrets_prefix=stack_name
        )

        CfnOutput(
            self,
            "pgstac-secret-arn",
            value=self.pgstac.secret.secret_arn,
            description=f"Arn of the Secrets Manager instance holding the connection info for the {construct_id} postgres database"
        )
