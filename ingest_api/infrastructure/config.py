from getpass import getuser
from typing import List, Optional

import aws_cdk
from pydantic import AnyHttpUrl, BaseSettings, Field, constr

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")


class IngestorConfig(BaseSettings):
    # S3 bucket names where TiTiler could do HEAD and GET Requests
    # specific private and public buckets MUST be added if you want to use s3:// urls
    # You can whitelist all bucket by setting `*`.
    # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html
    buckets: List = ["*"]

    # S3 key pattern to limit the access to specific items (e.g: "my_data/*.tif")
    key: str = "*"

    stage: str = Field(
        description=" ".join(
            [
                "Stage of deployment (e.g. 'dev', 'prod').",
                "Used as suffix for stack name.",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )
    owner: str = Field(
        description=" ".join(
            [
                "Name of primary contact for Cloudformation Stack.",
                "Used to tag generated resources",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")
    client_id: str = Field(description="The Cognito APP client ID")
    client_secret: Optional[str] = Field(
        "", description="The Cognito APP client secret"
    )
    cognito_domain: AnyHttpUrl = Field(
        description="The base url of the Cognito domain for authorization and token urls"
    )
    stac_db_security_group_id: str = Field(
        description="ID of Security Group used by pgSTAC DB"
    )

    raster_data_access_role_arn: Optional[AwsArn] = Field(  # type: ignore
        None, description="ARN of AWS Role used to validate access to S3 data"
    )

    raster_aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    ingest_root_path: str = Field("", description="Root path for ingest API")
    db_pgstac_version: str = Field(
        ...,
        description="Version of PgStac database, i.e. 0.5",
    )

    stac_api_url: str = Field(
        description="URL of STAC API Gateway endpoint used to serve STAC Items"
    )

    raster_api_url: str = Field(
        description="URL of Raster API Gateway endpoing used to serve asset tiles"
    )

    custom_host: Optional[str] = Field(
        None,
        description="Complete url of custom host including subdomain. Used to infer url of apis before app synthesis.",
    )

    stac_root_path: Optional[str] = Field(
        "",
        description="STAC API root path. Used to infer url of stac-api before app synthesis.",
    )

    raster_root_path: Optional[str] = Field(
        "",
        description="Raster API root path. Used to infer url of raster-api before app synthesis.",
    )

    disable_default_apigw_endpoint: Optional[bool] = Field(
        False,
        description="Boolean to disable default API gateway endpoints for stac, raster, and ingest APIs. Defaults to false."
    )

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_prefix = "VEDA_"

    @property
    def stack_name(self) -> str:
        return f"veda-stac-ingestion-{self.stage}"

    @property
    def env(self) -> aws_cdk.Environment:
        return aws_cdk.Environment(
            account=self.aws_account,
            region=self.aws_region,
        )

    @property
    def veda_stac_api_cf_url(self) -> str:
        """inferred cloudfront url of the stac api if app is configured with a custom host and root path"""
        if self.custom_host and self.stac_root_path:
            return f"https://{self.custom_host}{self.stac_root_path}"
        return self.stac_api_url

    @property
    def veda_raster_api_cf_url(self) -> str:
        """inferred cloudfront url of the raster api if app is configured with a custom host and root path"""
        if self.custom_host and self.raster_root_path:
            return f"https://{self.custom_host}{self.raster_root_path}"
        return self.raster_api_url
