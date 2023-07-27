#!/usr/bin/env python3
""" CDK Configuration for the veda-backend stack."""

from aws_cdk import App, Stack, Tags, aws_iam, aws_ec2
from constructs import Construct

from config import veda_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

from eoapi_cdk import PgStacApiLambda, StacIngestor, TitilerPgstacApiLambda

app = App()


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permission_boundary_policy = aws_iam.Policy.from_policy_name(
                self,
                "permission-boundary",
                veda_app_settings.permissions_boundary_policy_name,
            )
            aws_iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)


veda_stack = VedaStack(
    app,
    f"{veda_app_settings.app_name}-{veda_app_settings.stage_name()}",
    env=veda_app_settings.cdk_env(),
)

if veda_app_settings.vpc_id:
    vpc = VpcConstruct(
        veda_stack,
        "network",
        vpc_id=veda_app_settings.vpc_id,
        stage=veda_app_settings.stage_name(),
    )
else:
    vpc = VpcConstruct(veda_stack, "network", stage=veda_app_settings.stage_name())

database = RdsConstruct(
    veda_stack, "database", vpc.vpc, stage=veda_app_settings.stage_name()
)

domain = DomainConstruct(veda_stack, "domain", stage=veda_app_settings.stage_name())

raster_api = RasterApiLambdaConstruct(
    veda_stack,
    "raster-api",
    vpc=vpc.vpc,
    database=database,
    domain_name=domain.raster_domain_name,
)

stac_api = StacApiLambdaConstruct(
    veda_stack,
    "stac-api",
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain_name=domain.stac_domain_name,
)

eostac_api = PgStacApiLambda(
    veda_stack,
    "eostac",
    db=database.dbinstance,
    db_secret=database.pgstac.secret,
    vpc=vpc.vpc,
    subnet_selection=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED),
)

eoraster_api = TitilerPgstacApiLambda(
    veda_stack,
    "eoraster",
    db=database.dbinstance,
    db_secret=database.pgstac.secret,
    subnet_selection=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED),
    vpc=vpc.vpc,
)

eoingest_api = StacIngestor(
    veda_stack,
    "eoingest",
    data_access_role=aws_iam.Role.from_role_arn(
        veda_stack,
        "data-access-role",
        role_arn=veda_app_settings.veda_raster_data_access_role_arn),
    stac_db_secret=database.pgstac.secret,
    stac_db_security_group=database.dbinstance.connections.security_groups[0],
    stac_url=eostac_api.url,
    stage=veda_app_settings.stage_name(),
    subnet_selection=aws_ec2.SubnetSelection(
        subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED),
    vpc=vpc.vpc,
)

# TODO this conditional supports deploying a second set of APIs to a separate custom domain and should be removed if no longer necessary
if veda_app_settings.alt_domain():
    alt_domain = DomainConstruct(
        veda_stack,
        "alt-domain",
        stage=veda_app_settings.stage_name(),
        alt_domain=True,
    )

    alt_raster_api = RasterApiLambdaConstruct(
        veda_stack,
        "alt-raster-api",
        vpc=vpc.vpc,
        database=database,
        domain_name=alt_domain.raster_domain_name,
    )

    alt_stac_api = StacApiLambdaConstruct(
        veda_stack,
        "alt-stac-api",
        vpc=vpc.vpc,
        database=database,
        raster_api=raster_api,
        domain_name=alt_domain.stac_domain_name,
    )

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": "ds",
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
