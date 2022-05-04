"""API settings."""

from functools import lru_cache
import base64
import json
import os
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
import pydantic

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

class _ApiSettings(pydantic.BaseSettings):
    """API settings"""

    name: str = "delta-raster"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False

    # MosaicTiler settings
    enable_mosaic_search: bool = False

    # @pydantic.validator("pgstac_secret_arn")
    # def set_secret_in_environment(cls, secretsmanager_arn: str) -> "_ApiSettings":
    #     """Set environment variables in lambda from aws secret"""
    #     secret = get_secret_dict(SecretId=secretsmanager_arn)
        # os.environ["POSTGRES_DBNAME"] = secret["dbname"]
        # os.environ["POSTGRES_USER"] = secret["username"]
        # os.environ["POSTGRES_PASS"] = secret["password"]
        # os.environ["POSTGRES_PORT"] = secret["port"]
        # os.environ["POSTGRES_HOST"] = secret["host"]

    @pydantic.validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_RASTER_"


@lru_cache()
def ApiSettings() -> _ApiSettings:
    """
    This function returns a cached instance of the APISettings object.
    Caching is used to prevent re-reading the environment every time the API settings are used in an endpoint.
    If you want to change an environment variable and reset the cache (e.g., during testing), this can be done
    using the `lru_cache` instance method `get_api_settings.cache_clear()`.
    From https://github.com/dmontagu/fastapi-utils/blob/af95ff4a8195caaa9edaa3dbd5b6eeb09691d9c7/fastapi_utils/api_settings.py#L60-L69
    """
    return _ApiSettings()

# class _PostgresSettings(pydantic.BaseSettings):
#     """Postgres-specific API settings.
#     Attributes:
#         postgres_user: postgres username.
#         postgres_pass: postgres password.
#         postgres_host: database hostname.
#         postgres_port: database port.
#         postgres_dbname: database name.
#     """
#     pgstac_secret_arn: Optional[str] = None
#     postgres_user: str
#     postgres_pass: str
#     postgres_host: str
#     postgres_port: str
#     postgres_dbname: str

#     # see https://www.psycopg.org/psycopg3/docs/api/pool.html#the-connectionpool-class for options
#     db_min_conn_size: int = 1  # The minimum number of connection the pool will hold
#     db_max_conn_size: int = 10  # The maximum number of connections the pool will hold
#     db_max_queries: int = (
#         50000  # Maximum number of requests that can be queued to the pool
#     )
#     db_max_idle: float = 300  # Maximum time, in seconds, that a connection can stay unused in the pool before being closed, and the pool shrunk.
#     db_num_workers: int = (
#         3  # Number of background worker threads used to maintain the pool state
#     )

#     @classmethod
#     def from_secret(cls, secretsmanager_arn: str) -> "_PostgresSettings":
#         """Get database connection settings from AWS secret"""

#         secret = get_secret_dict(secretsmanager_arn)

#         # Hack--add postgres conn info to environment
#         os.environ["POSTGRES_DBNAME"] = secret["dbname"]
#         os.environ["POSTGRES_USER"] = secret["username"]
#         os.environ["POSTGRES_PASS"] = secret["password"]
#         os.environ["POSTGRES_PORT"] = secret["port"]
#         os.environ["POSTGRES_HOST"] = secret["host"]

#         return cls.parse_obj(
#             {
#                 "postgres_host": secret["host"],
#                 "postgres_dbname": secret["dbname"],
#                 "postgres_user": secret["username"],
#                 "postgres_pass": secret["password"],
#                 "postgres_port": secret["port"],
#             }
#         )

#     class Config:
#         """model config"""

#         env_file = ".env"

#     @property
#     def connection_string(self):
#         """Create reader psql connection string."""
#         return f"postgresql://{self.postgres_user}:{self.postgres_pass}@{self.postgres_host}:{self.postgres_port}/{self.postgres_dbname}"


# @lru_cache()
# def PostgresSettings() -> _PostgresSettings:
#     """Postgres Settings."""
#     return _PostgresSettings()

def put_postgres_env(secretsmanager_arn: str) -> None:
    """Get database connection settings from AWS secret"""

    secret = get_secret_dict(secretsmanager_arn)

    # Hack--add postgres conn info to environment
    os.environ["POSTGRES_DBNAME"] = secret["dbname"]
    os.environ["POSTGRES_USER"] = secret["username"]
    os.environ["POSTGRES_PASS"] = secret["password"]
    os.environ["POSTGRES_PORT"] = str(secret["port"])
    os.environ["POSTGRES_HOST"] = secret["host"]