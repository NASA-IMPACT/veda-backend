"""CDK Construct for veda-backend RDS instance."""
import json
import os
from typing import List, Optional, Union

from aws_cdk import (
    CfnOutput,
    CustomResource,
    Duration,
    RemovalPolicy,
    SecretValue,
    Stack,
    aws_ec2,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_rds,
    aws_secretsmanager,
)
from constructs import Construct

from .config import features_db_settings


# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
class BootstrapTIPG(Construct):
    """
    Given an RDS database, connect and create a database, user, and password
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        database: Union[aws_rds.DatabaseInstance, aws_rds.DatabaseInstanceFromSnapshot],
        new_dbname: str,
        new_username: str,
        secrets_prefix: str,
        host: str,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        handler = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"),
                file="features_api_database/runtime/Dockerfile",
            ),
            timeout=Duration.minutes(2),
            vpc=database.vpc,
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
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
                        "host": host,
                        "username": new_username,
                    }
                ),
                generate_string_key="password",
                exclude_punctuation=True,
            ),
            description=f"TIPG database bootsrapped by {Stack.of(self).stack_name} stack",
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
                "new_user_secret_arn": self.secret.secret_arn,
            },
            removal_policy=RemovalPolicy.RETAIN,  # This retains the custom resource (which doesn't really exist), not the database
        )


# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
# https://github.com/NASA-IMPACT/hls-sentinel2-downloader-serverless/blob/main/cdk/downloader_stack.py
# https://github.com/aws-samples/aws-cdk-examples/blob/master/python/new-vpc-alb-asg-mysql/cdk_vpc_ec2/cdk_rds_stack.py
class RdsConstruct(Construct):
    """Provisions an empty RDS database, fed to the BootstrapTIPG construct
    which provisions and executes a lambda function that loads the PGSTAC
    schema in the database"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: aws_ec2.Vpc,
        subnet_ids: Optional[List],
        stage: str,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        stack_name = Stack.of(self).stack_name

        # Custom parameter group
        engine = aws_rds.DatabaseInstanceEngine.postgres(
            version=aws_rds.PostgresEngineVersion.of(
                features_db_settings.rds_engine_full_version,
                features_db_settings.rds_engine_major_version,
            )
        )

        # RDS Instance Type
        rds_instance_type = aws_ec2.InstanceType.of(
            aws_ec2.InstanceClass[features_db_settings.rds_instance_class],
            aws_ec2.InstanceSize[features_db_settings.rds_instance_size],
        )

        #  version=aws_rds.PostgresEngineVersion.postgres_major_version(features_db_settings.rds_engine_version)
        parameter_group = aws_rds.ParameterGroup(
            self,
            "parameter-group",
            engine=engine,
            parameters={
                "max_locks_per_transaction": features_db_settings.max_locks_per_transaction,
                "work_mem": features_db_settings.work_mem,
                "temp_buffers": features_db_settings.temp_buffers,
            },
        )

        # Configure accessibility
        if subnet_ids:
            self.vpc_subnets = aws_ec2.SubnetSelection(
                subnets=[
                    aws_ec2.Subnet.from_subnet_attributes(
                        self, f"Subnet{i}", subnet_id=subnet_id
                    )
                    for i, subnet_id in enumerate(subnet_ids)
                ]
            )
        else:
            subnet_type = (
                aws_ec2.SubnetType.PRIVATE_WITH_EGRESS
                if not features_db_settings.publicly_accessible
                else aws_ec2.SubnetType.PUBLIC
            )
            self.vpc_subnets = aws_ec2.SubnetSelection(subnet_type=subnet_type)

        # Database Configurations
        database_config = {
            "id": "rds",
            "instance_identifier": f"{stack_name}-postgres",
            "vpc": vpc,
            "engine": engine,
            "instance_type": rds_instance_type,
            "vpc_subnets": self.vpc_subnets,
            "deletion_protection": True,
            "removal_policy": RemovalPolicy.RETAIN,
            "publicly_accessible": features_db_settings.publicly_accessible,
            "parameter_group": parameter_group,
        }

        if features_db_settings.rds_encryption:
            database_config["storage_encrypted"] = features_db_settings.rds_encryption

        # Create a new database instance from snapshot if provided
        if features_db_settings.snapshot_id:
            # For the database from snapshot we will need a new master secret
            snapshot_credentials = aws_rds.SnapshotCredentials.from_generated_secret(
                username=features_db_settings.admin_user
            )

            database = aws_rds.DatabaseInstanceFromSnapshot(
                self,
                snapshot_identifier=features_db_settings.snapshot_id,
                credentials=snapshot_credentials,
                **database_config,
            )

        # Or create/update RDS Resource
        else:
            database = aws_rds.DatabaseInstance(self, **database_config)

        hostname = database.instance_endpoint.hostname
        self.db_security_group = database.connections.security_groups[0]
        self.is_publicly_accessible = features_db_settings.publicly_accessible

        # Use custom resource to bootstrap PgSTAC database
        self.pgstac = BootstrapTIPG(
            self,
            "features-tipg-db",
            database=database,
            new_dbname=features_db_settings.dbname,
            new_username=features_db_settings.user,
            secrets_prefix=stack_name,
            host=hostname,
        )

        CfnOutput(
            self,
            "pgstac-secret-name",
            value=self.pgstac.secret.secret_arn,
            export_name=f"{stack_name}-stac-db-secret-name",
            description=f"Name of the Secrets Manager instance holding the connection info for the {construct_id} postgres database",
        )
        if self.proxy:
            CfnOutput(
                self,
                "rds-proxy-endpoint",
                value=self.proxy.endpoint,
            )
