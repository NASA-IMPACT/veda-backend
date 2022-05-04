"""API settings."""

import base64
import json
import os

import boto3
import pydantic
from botocore.exceptions import ClientError


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


class ApiSettings(pydantic.BaseSettings):
    """API settings"""

    name: str = "delta-raster"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False

    # MosaicTiler settings
    enable_mosaic_search: bool = False

    pgstac_secret_arn: str

    @pydantic.validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_RASTER_"


def put_postgres_env(secretsmanager_arn: str) -> None:
    """Get database connection settings from AWS secret and put in environment"""

    secret = get_secret_dict(secretsmanager_arn)
    os.environ["POSTGRES_DBNAME"] = secret["dbname"]
    os.environ["POSTGRES_USER"] = secret["username"]
    os.environ["POSTGRES_PASS"] = secret["password"]
    os.environ["POSTGRES_PORT"] = str(secret["port"])
    os.environ["POSTGRES_HOST"] = secret["host"]
