"""API settings."""

import base64
import json
import os
from typing import Optional

import boto3
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from rasterio.session import AWSSession
from typing_extensions import Annotated

from titiler.pgstac.settings import PostgresSettings


def get_secret_dict(secret_name: str):
    """Retrieve secrets from AWS Secrets Manager

    Args:
        secret_name (str): name of aws secrets manager secret containing database connection secrets
        profile_name (str, optional): optional name of aws profile for use in debugger only

    Returns:
        secrets (dict): decrypted secrets in dict
    """

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    get_secret_value_response = client.get_secret_value(SecretId=secret_name)

    if "SecretString" in get_secret_value_response:
        return json.loads(get_secret_value_response["SecretString"])
    else:
        return json.loads(base64.b64decode(get_secret_value_response["SecretBinary"]))


def get_role_credentials(role_arn: str):
    """Get AWS IAM role credentials from ARN"""

    sts = boto3.client("sts")
    return sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="AssumeRoleSession",
    )["Credentials"]


class ApiSettings(BaseSettings):
    """API settings"""

    name: str = "veda-raster"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False
    root_path: Optional[str] = None

    # MosaicTiler settings
    enable_mosaic_search: bool = False

    pgstac_secret_arn: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "env_prefix": "VEDA_RASTER_",
    }

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    def load_postgres_settings(self) -> "PostgresSettings":
        """Load postgres connection params from AWS secret"""

        if self.pgstac_secret_arn:
            secret = get_secret_dict(self.pgstac_secret_arn)
            return PostgresSettings(
                postgres_user=secret["username"],
                postgres_pass=secret["password"],
                postgres_host=secret["host"],
                postgres_port=int(secret["port"]),
                postgres_dbname=secret["dbname"],
            )
        else:
            return PostgresSettings()

    data_access_role_arn: Annotated[
        Optional[str],
        Field(
            description="Resource name of role permitting access to specified external S3 buckets"
        ),
    ] = None

    export_assume_role_creds_as_envs: Annotated[
        bool,
        Field(
            description="enables 'get_gdal_config' flow to export AWS credentials as os env vars",
        ),
    ] = False

    def get_gdal_config(self):
        """return default aws session config or assume role data_access_role_arn credentials session"""
        # STS assume data access role for session credentials
        if self.data_access_role_arn:
            try:
                data_access_credentials = get_role_credentials(
                    self.data_access_role_arn
                )

                # hack for issue https://github.com/NASA-IMPACT/veda-backend/issues/192
                # which forces any nested `rasterio.Env` context managers (which run in separate threads)
                # to pick up the assume-role `AWS_*` os env vars and re-init from there via:
                # https://github.com/rasterio/rasterio/blob/main/rasterio/env.py#L204-L205
                if self.export_assume_role_creds_as_envs:
                    os.environ["AWS_ACCESS_KEY_ID"] = data_access_credentials[
                        "AccessKeyId"
                    ]
                    os.environ["AWS_SECRET_ACCESS_KEY"] = data_access_credentials[
                        "SecretAccessKey"
                    ]
                    os.environ["AWS_SESSION_TOKEN"] = data_access_credentials[
                        "SessionToken"
                    ]

                return {
                    "session": AWSSession(
                        aws_access_key_id=data_access_credentials["AccessKeyId"],
                        aws_secret_access_key=data_access_credentials[
                            "SecretAccessKey"
                        ],
                        aws_session_token=data_access_credentials["SessionToken"],
                    )
                }
            except Exception as e:
                print(
                    f"Unable to assume role {self.data_access_role_arn} with exception={e}"
                )
                return {}
        else:
            # Use the default role of this lambda
            return {}
