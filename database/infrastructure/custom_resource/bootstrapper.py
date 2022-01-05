import os
import json
from aws_cdk import (
    aws_ec2,
    aws_lambda,
    aws_rds,
    aws_secretsmanager,
    CustomResource, Duration, Stack
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
            "LambdaFunction",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"), 
                file="database/infrastructure/custom_resource/Dockerfile"
            ),
            timeout=Duration.minutes(2),
            vpc=database.vpc
        )

        self.secret = aws_secretsmanager.Secret(
            self,
            construct_id, # contains identifier
            secret_name=os.path.join(secrets_prefix, f"{construct_id}Secret{self.node.id}"),
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
            description=f"{construct_id} bootstrapped database deployed by {Stack.of(self).stack_name}"
        )

        # Allow lambda to...
        # read new user secret
        self.secret.grant_read(handler)
        # read database secret
        database.secret.grant_read(handler)
        # connect to database
        database.connections.allow_from(handler, port_range=aws_ec2.Port.tcp(5432))

        CustomResource(
            scope=scope,
            id="BootstrapperCustomResource",
            service_token=handler.function_arn,
            properties={
                "conn_secret_arn": database.secret.secret_arn,
                "new_user_secret_arn": self.secret.secret_arn
            }
        )
