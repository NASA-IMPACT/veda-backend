from typing import Optional

from aws_cdk import Aspects, Stack, aws_iam
from constructs import Construct

from database.infrastructure.construct import RdsConstruct
from ingest_api.infrastructure.config import IngestorConfig as ingest_config
from ingest_api.infrastructure.construct import ApiConstruct as ingest_api_construct
from ingest_api.infrastructure.construct import IngestorConstruct as ingestor_construct
from network.infrastructure.construct import VpcConstruct
from permissions_boundary.infrastructure.construct import PermissionsBoundaryAspect
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        git_sha: str,
        stage: str,
        vpc_id: Optional[str] = None,
        subnet_ids: Optional[list] = None,
        permissions_boundary_policy_name: Optional[str] = None,
        **kwargs,
    ) -> None:

        super().__init__(scope, id, **kwargs)

        if permissions_boundary_policy_name:
            permissions_boundary_policy = (
                aws_iam.ManagedPolicy.from_managed_policy_name(
                    self,
                    "permissions-boundary",
                    permissions_boundary_policy_name,
                )
            )
            aws_iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)
            Aspects.of(self).add(PermissionsBoundaryAspect(permissions_boundary_policy))

        if vpc_id:
            vpc = VpcConstruct(
                self,
                "network",
                vpc_id=vpc_id,
                stage=stage,
            )
        else:
            vpc = VpcConstruct(self, "network", stage=stage)

        database = RdsConstruct(
            self,
            "database",
            vpc=vpc.vpc,
            subnet_ids=subnet_ids,
            stage=stage,
        )

        raster_api = RasterApiLambdaConstruct(
            self,
            "raster-api",
            stage=stage,
            vpc=vpc.vpc,
            database=database,
        )

        stac_api = StacApiLambdaConstruct(
            self,
            "stac-api",
            stage=stage,
            vpc=vpc.vpc,
            database=database,
            raster_api=raster_api,
        )

        db_security_group = database.db_security_group

        # ingestor config requires references to other resources, but can be shared between ingest api and bulk ingestor
        ingestor_config = ingest_config(
            stage=stage,
            stac_db_security_group_id=db_security_group.security_group_id,
            stac_api_url=stac_api.stac_api.url,
            raster_api_url=raster_api.raster_api.url,
            git_sha=git_sha,
        )

        ingest_api = ingest_api_construct(
            self,
            "ingest-api",
            config=ingestor_config,
            db_secret=database.pgstac.secret,
            db_vpc=vpc.vpc,
        )

        ingestor_construct(
            self,
            "IngestorConstruct",
            config=ingestor_config,
            table=ingest_api.table,
            db_secret=database.pgstac.secret,
            db_vpc=vpc.vpc,
        )
