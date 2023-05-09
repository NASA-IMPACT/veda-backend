"""CDK Construct for veda-backend RDS instance."""
import json
import os
from typing import Union

from aws_cdk import (
    CfnOutput,
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_rds,
    aws_secretsmanager,
)
from constructs import Construct

from .config import veda_db_settings


# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
class BootstrapPgStac(Construct):
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
        stage: str,
        host: str,
    ) -> None:
        """."""
        super().__init__(scope, construct_id)

        pgstac_version = veda_db_settings.pgstac_version
        veda_schema_version = veda_db_settings.schema_version

        handler = aws_lambda.Function(
            self,
            "lambda",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"),
                file="database/runtime/Dockerfile",
                build_args={"PGSTAC_VERSION": pgstac_version},
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
            description=f"Pgstac database bootsrapped by {Stack.of(self).stack_name} stack",
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
                # By setting pgstac_version in the properties assures
                # that Create/Update events will be passed to the service token
                "pgstac_version": pgstac_version,
                "conn_secret_arn": database.secret.secret_arn,
                "new_user_secret_arn": self.secret.secret_arn,
                "veda_schema_version": veda_schema_version,
            },
            removal_policy=RemovalPolicy.RETAIN,  # This retains the custom resource (which doesn't really exist), not the database
        )


# https://github.com/developmentseed/eoAPI/blob/master/deployment/cdk/app.py
# https://github.com/NASA-IMPACT/hls-sentinel2-downloader-serverless/blob/main/cdk/downloader_stack.py
# https://github.com/aws-samples/aws-cdk-examples/blob/master/python/new-vpc-alb-asg-mysql/cdk_vpc_ec2/cdk_rds_stack.py
class RdsConstruct(Construct):
    """Provisions an empty RDS database, fed to the BootstrapPgStac construct
    which provisions and executes a lambda function that loads the PGSTAC
    schema in the database"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: aws_ec2.Vpc,
        stage: str,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        stack_name = Stack.of(self).stack_name

        # Configure accessibility
        subnet_type = (
            aws_ec2.SubnetType.PRIVATE_ISOLATED
            if veda_db_settings.publicly_accessible is False
            else aws_ec2.SubnetType.PUBLIC
        )

        # Custom parameter group
        engine = aws_rds.DatabaseInstanceEngine.postgres(
            version=aws_rds.PostgresEngineVersion.VER_14
        )
        parameter_group = aws_rds.ParameterGroup(
            self,
            "parameter-group",
            engine=engine,
            parameters={
                "max_locks_per_transaction": veda_db_settings.max_locks_per_transaction,
                "work_mem": veda_db_settings.work_mem,
                "temp_buffers": veda_db_settings.temp_buffers,
            },
        )

        # Create a new database instance from snapshot if provided
        if veda_db_settings.snapshot_id:
            # For the database from snapshot we will need a new master secret
            credentials = aws_rds.SnapshotCredentials.from_generated_secret(
                username=veda_db_settings.admin_user
            )

            database = aws_rds.DatabaseInstanceFromSnapshot(
                self,
                id="rds",
                snapshot_identifier=veda_db_settings.snapshot_id,
                instance_identifier=f"{stack_name}-postgres",
                vpc=vpc,
                engine=engine,
                instance_type=aws_ec2.InstanceType.of(
                    aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.SMALL
                ),
                vpc_subnets=aws_ec2.SubnetSelection(subnet_type=subnet_type),
                deletion_protection=True,
                removal_policy=RemovalPolicy.RETAIN,
                publicly_accessible=veda_db_settings.publicly_accessible,
                credentials=credentials,
                parameter_group=parameter_group,
            )

        # Or create/update RDS Resource
        else:
            database = aws_rds.DatabaseInstance(
                self,
                id="rds",
                instance_identifier=f"{stack_name}-postgres",
                vpc=vpc,
                engine=engine,
                instance_type=aws_ec2.InstanceType.of(
                    aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.SMALL
                ),
                vpc_subnets=aws_ec2.SubnetSelection(subnet_type=subnet_type),
                deletion_protection=True,
                removal_policy=RemovalPolicy.RETAIN,
                publicly_accessible=veda_db_settings.publicly_accessible,
                parameter_group=parameter_group,
            )

        hostname = database.instance_endpoint.hostname
        self.db_security_group = database.connections.security_groups[
            0
        ].security_group_id
        self.db_is_private = veda_db_settings.private_subnets

        # Use custom resource to bootstrap PgSTAC database
        self.pgstac = BootstrapPgStac(
            self,
            "pgstac",
            database=database,
            new_dbname=veda_db_settings.dbname,
            new_username=veda_db_settings.user,
            secrets_prefix=stack_name,
            stage=stage,
            host=hostname,
        )

        self.proxy = None
        if veda_db_settings.use_rds_proxy:
            # secret for non-admin user
            proxy_secret = self.pgstac.secret

            proxy_role = aws_iam.Role(
                self,
                "RDSProxyRole",
                assumed_by=aws_iam.ServicePrincipal("rds.amazonaws.com"),
            )
            self.proxy = aws_rds.DatabaseProxy(
                self,
                proxy_target=aws_rds.ProxyTarget.from_instance(database),
                id="RdsProxy",
                vpc=vpc,
                secrets=[database.secret, proxy_secret],
                db_proxy_name=f"veda-backend-{stage}-proxy",
                role=proxy_role,
                require_tls=False,
                debug_logging=False,
            )

            # Allow connections to the proxy from the same security groups as the DB
            for sg in database.connections.security_groups:
                self.proxy.connections.add_security_group(sg)

        CfnOutput(
            self,
            "pgstac-secret-name",
            value=self.pgstac.secret.secret_arn,
            description=f"Name of the Secrets Manager instance holding the connection info for the {construct_id} postgres database",
        )
