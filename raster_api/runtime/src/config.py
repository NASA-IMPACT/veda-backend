"""API settings."""

import base64
import json
from typing import Optional

import boto3
import pydantic

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


class ApiSettings(pydantic.BaseSettings):
    """API settings"""

    name: str = "delta-raster"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False

    # MosaicTiler settings
    enable_mosaic_search: bool = False

    pgstac_secret_arn: Optional[str]

    @pydantic.validator("cors_origins")
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
                postgres_port=str(secret["port"]),
                postgres_dbname=secret["dbname"],
            )
        else:
            return PostgresSettings()

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_RASTER_"


# from titiler.pgstac.settings import PostgresSettings
# class PostgresSettings(pydantic.BaseSettings):
#     """Postgres-specific API settings.
#     Attributes:
#         postgres_user: postgres username.
#         postgres_pass: postgres password.
#         postgres_host: database hostname.
#         postgres_port: database port.
#         postgres_dbname: database name.
#     """

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

#     class Config:
#         """model config"""

#         env_file = ".env"

#     @property
#     def connection_string(self):
#         """Create reader psql connection string."""
#         return f"postgresql://{self.postgres_user}:{self.postgres_pass}@{self.postgres_host}:{self.postgres_port}/{self.postgres_dbname}"
