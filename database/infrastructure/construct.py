import os
import json

from aws_cdk import (
    aws_ec2,
    aws_lambda,
    aws_rds,
    aws_secretsmanager,
    CfnOutput, 
    CustomResource,
    Duration,
    RemovalPolicy, 
    Stack,
)
from constructs import Construct

# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
class BootstrapPgStac(Construct):
    """
    Given an RDS database, connect and create a database, user, and password
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        database: aws_rds.DatabaseInstance,
        new_dbname: str,
        new_username: str,
        secrets_prefix: str
    ) -> None:
        super().__init__(scope, construct_id)

        handler = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"), 
                file="database/runtime/Dockerfile"
            ),
            timeout=Duration.minutes(2),
            vpc=database.vpc
        )

        self.secret = aws_secretsmanager.Secret(
            self,
            "secret",
            secret_name=os.path.join(secrets_prefix, construct_id, self.node.addr[-8:]),
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "dbname": new_dbname,
                        "engine": "postgres",
                        "port": 5432,
                        "host": database.instance_endpoint.hostname,
                        "username": new_username
                    }
                ),
                generate_string_key="password",
                exclude_punctuation=True
            ),
            description=f"Pgstac database bootsrapped by {Stack.of(self).stack_name} stack"
        )

        # Allow lambda to...
        # read new user secret
        self.secret.grant_read(handler)
        # read database secret
        database.secret.grant_read(handler)
        # connect to database
        database.connections.allow_from(handler, port_range=aws_ec2.Port.tcp(5432))
        
        self.connections = database.connections

        CustomResource(
            scope=scope,
            id="bootstrapper",
            service_token=handler.function_arn,
            properties={
                "conn_secret_arn": database.secret.secret_arn,
                "new_user_secret_arn": self.secret.secret_arn
            },
            removal_policy=RemovalPolicy.RETAIN # This retains the custom resource (which doesn't really exist), not the database
        )

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
