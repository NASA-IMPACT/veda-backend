"""Stack Configs."""

from typing import Optional
from functools import lru_cache
import pydantic_settings
import boto3
import json
import base64


@lru_cache()
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


class FeaturesAPISettings(pydantic_settings.BaseSettings):
    """Application settings"""

    name: str = "veda-features-api"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False
    root_path: Optional[str] = None
    add_tiles_viewer: bool = True

    catalog_ttl: int = 300  # seconds

    postgis_secret_arn: Optional[str] = None

    def load_postgres_settings(self) -> "PostgresSettings":
        from tipg.settings import PostgresSettings

        if self.postgis_secret_arn:
            print(f"loading {self.postgis_secret_arn}")
            secret = get_secret_dict(self.postgis_secret_arn)
            return PostgresSettings(
                postgres_user=secret["username"],
                postgres_pass=secret["password"],
                postgres_host=secret["host"],
                postgres_port=int(secret["port"]),
                postgres_dbname=secret["dbname"],
            )
        else:
            return PostgresSettings()

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "env_prefix": "VEDA_FEATURES_",
    }
