#!/usr/bin/env python3
""" CDK Configuration for the veda-backend stack."""

import subprocess

from aws_cdk import App, Aspects, Stack, Tags, aws_iam
from constructs import Construct

from config import veda_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from ingest_api.infrastructure.config import IngestorConfig as ingest_config
from ingest_api.infrastructure.construct import ApiConstruct as ingest_api_construct
from ingest_api.infrastructure.construct import IngestorConstruct as ingestor_construct
from network.infrastructure.construct import VpcConstruct
from permissions_boundary.infrastructure.construct import PermissionsBoundaryAspect
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from s3_website.infrastructure.construct import VedaWebsite
from stac_api.infrastructure.construct import StacApiLambdaConstruct

from eoapi_cdk import StacBrowser

app = App()
if veda_app_settings.bootstrap_qualifier:
    app.node.set_context(
        "@aws-cdk/core:bootstrapQualifier", veda_app_settings.bootstrap_qualifier
    )


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permissions_boundary_policy = (
                aws_iam.ManagedPolicy.from_managed_policy_name(
                    self,
                    "permissions-boundary",
                    veda_app_settings.permissions_boundary_policy_name,
                )
            )
            aws_iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)
            Aspects.of(self).add(PermissionsBoundaryAspect(permissions_boundary_policy))


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
    veda_stack,
    "database",
    vpc=vpc.vpc,
    subnet_ids=veda_app_settings.subnet_ids,
    stage=veda_app_settings.stage_name(),
)

domain = DomainConstruct(veda_stack, "domain", stage=veda_app_settings.stage_name())

raster_api = RasterApiLambdaConstruct(
    veda_stack,
    "raster-api",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    database=database,
    domain=domain,
)

stac_api = StacApiLambdaConstruct(
    veda_stack,
    "stac-api",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain=domain,
)

website = VedaWebsite(
    veda_stack, "stac-browser-bucket", stage=veda_app_settings.stage_name()
)

# Only create a stac browser if we can infer the catalog url from configuration before synthesis (API Gateway URL not yet available)
stac_catalog_url = veda_app_settings.get_stac_catalog_url()
if stac_catalog_url:
    stac_browser = StacBrowser(
        veda_stack,
        "stac-browser",
        github_repo_tag=veda_app_settings.stac_browser_tag,
        stac_catalog_url=stac_catalog_url,
        bucket_arn=website.bucket.bucket_arn,
    )

db_secret_name = database.pgstac.secret.secret_name
db_security_group = database.db_security_group

base_api_url = f"https://{veda_app_settings.stage_name()}.{veda_app_settings.veda_custom_host}".strip(
    "/"
)
stac_api_url = f"{base_api_url}{veda_app_settings.veda_stac_root_path}/"
raster_api_url = f"{base_api_url}{veda_app_settings.veda_raster_root_path}/"

# ingestor config requires references to other resources, but can be shared between ingest api and bulk ingestor
ingestor_config = ingest_config(
    stage=veda_app_settings.stage_name(),
    stac_db_security_group_id=db_security_group.security_group_id,
    stac_api_url=stac_api_url,
    raster_api_url=raster_api_url,
)


ingest_api = ingest_api_construct(
    veda_stack,
    "ingest-api",
    config=ingestor_config,
    db_secret=database.pgstac.secret,
    db_vpc=vpc.vpc,
    db_vpc_subnets=database.vpc_subnets,
    domain=domain,
)

ingestor = ingestor_construct(
    veda_stack,
    "IngestorConstruct",
    config=ingestor_config,
    table=ingest_api.table,
    db_secret=database.pgstac.secret,
    db_vpc=vpc.vpc,
    db_vpc_subnets=database.vpc_subnets,
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
        stage=veda_app_settings.stage_name(),
        vpc=vpc.vpc,
        database=database,
        domain_name=alt_domain.raster_domain_name,
    )

    alt_stac_api = StacApiLambdaConstruct(
        veda_stack,
        "alt-stac-api",
        stage=veda_app_settings.stage_name(),
        vpc=vpc.vpc,
        database=database,
        raster_api=raster_api,
        domain_name=alt_domain.stac_domain_name,
    )

    alt_ingest_api = ingest_api_construct(
        veda_stack,
        "alt-ingest-api",
        config=ingestor_config,
        db_secret=database.pgstac.secret,
        db_vpc=vpc.vpc,
        domain_name=alt_domain.ingest_domain_name,
    )

git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
try:
    git_tag = subprocess.check_output(["git", "describe", "--tags"]).decode().strip()
except subprocess.CalledProcessError:
    git_tag = "no-tag"

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": veda_app_settings.owner,
    "GitCommit": git_sha,
    "GitTag": git_tag,
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
