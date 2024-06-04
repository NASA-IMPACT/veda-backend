from getpass import getuser
from typing import Optional

import aws_cdk
from pydantic import AnyHttpUrl, BaseSettings, Field, constr

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")


class IngestorConfig(BaseSettings):
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

    stac_api_url: str = Field(description="URL of STAC API used to serve STAC Items")

    raster_api_url: str = Field(
        description="URL of Raster API used to serve asset tiles"
    )

    ingest_root_path: str = Field("", description="Root path for ingest API")
    custom_host: Optional[str] = Field(description="Custom host name")

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
