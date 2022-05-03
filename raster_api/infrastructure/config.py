"""Settings for Raster API - any environment variables starting with
`DELTA_RASTER_` will overwrite the values of variables in this file
"""
import base64
import json
import os
from typing import Dict, List, Optional

import boto3
import pydantic
from botocore.exceptions import ClientError


def get_secret_dict(secret_name: str) -> None:
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

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDeniedException":
            raise e
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if "SecretString" in get_secret_value_response:
            return json.loads(get_secret_value_response["SecretString"])
        else:
            return json.loads(
                base64.b64decode(get_secret_value_response["SecretBinary"])
            )


class deltaRasterSettings(pydantic.BaseSettings):
    """Application settings"""

    # Default options are optimized for CloudOptimized GeoTIFF
    # For more information on GDAL env see: https://gdal.org/user/configoptions.html
    # or https://developmentseed.org/titiler/advanced/performance_tuning/
    env: Dict = {
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff",
        "GDAL_CACHEMAX": "200",  # 200 mb
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "GDAL_INGESTED_BYTES_AT_OPEN": "32768",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MULTIPLEX": "YES",
        "GDAL_HTTP_VERSION": "2",
        "PYTHONWARNINGS": "ignore",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": "5000000",  # 5 MB (per file-handle)
        "DB_MIN_CONN_SIZE": "1",
        "DB_MAX_CONN_SIZE": "1",
    }

    # S3 bucket names where TiTiler could do HEAD and GET Requests
    # specific private and public buckets MUST be added if you want to use s3:// urls
    # You can whitelist all bucket by setting `*`.
    # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html
    buckets: List = ["*"]

    # S3 key pattern to limit the access to specific items (e.g: "my_data/*.tif")
    key: str = "*"

    timeout: int = 10  # seconds
    memory: int = 3008  # Mb

    # MosaicTiler settings
    enable_mosaic_search: bool = False

    pgstac_secret_arn: Optional[str] = None

    @pydantic.validator("pgstac_secret_arn")
    def set_secret_in_environment(cls, v):
        """Set environment variables in lambda from aws secret"""
        try:
            secret = get_secret_dict(SecretId=cls.pgstac_secret_arn)
            os.environ["POSTGRES_DBNAME"] = secret["dbname"]
            os.environ["POSTGRES_USER"] = secret["username"]
            os.environ["POSTGRES_PASS"] = secret["password"]
            os.environ["POSTGRES_PORT"] = secret["port"]
            os.environ["POSTGRES_HOST"] = secret["host"]
        except Exception:
            pass

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_RASTER_"


delta_raster_settings = deltaRasterSettings()
