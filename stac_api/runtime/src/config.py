"""API settings.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac"""

import base64
import json
from functools import lru_cache
from typing import Optional

import boto3
from pydantic import AnyHttpUrl, BaseSettings, Field, validator, root_validator

from fastapi.responses import ORJSONResponse
from stac_fastapi.api.models import create_get_request_model, create_post_request_model

# from stac_fastapi.pgstac.extensions import QueryExtension
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    FilterExtension,
    QueryExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.pgstac.config import Settings
from stac_fastapi.pgstac.transactions import BulkTransactionsClient, TransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch


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


class _ApiSettings(BaseSettings):
    """API settings"""

    project_name: Optional[str] = "veda"
    project_description: Optional[str] = None
    cors_origins: str = "*"
    cachecontrol: str = "max-age=30,must-revalidate,s-maxage=604800"
    debug: bool = False
    root_path: Optional[str] = None
    pgstac_secret_arn: Optional[str]
    stage: Optional[str] = None

    userpool_id: Optional[str] = Field("", description="The Cognito Userpool used for authentication")
    cognito_domain: Optional[AnyHttpUrl] = Field(
        description="The base url of the Cognito domain for authorization and token urls"
    )
    client_id: Optional[str] = Field(description="The Cognito APP client ID")
    client_secret: Optional[str] = Field("", description="The Cognito APP client secret")
    enable_transactions: bool = Field(False, description="Whether to enable transactions")

    @root_validator
    def check_transaction_fields(cls, values):
        enable_transactions = values.get('enable_transactions')

        if enable_transactions:
            missing_fields = [field for field in ['userpool_id', 'cognito_domain', 'client_id'] if not values.get(field)]
            if missing_fields:
                raise ValueError(f"When 'enable_transactions' is True, the following fields must be provided: {', '.join(missing_fields)}")
        return values

    @property
    def jwks_url(self) -> AnyHttpUrl:
        """JWKS url"""
        region = self.userpool_id.split("_")[0]
        return f"https://cognito-idp.{region}.amazonaws.com/{self.userpool_id}/.well-known/jwks.json"

    @property
    def cognito_authorization_url(self) -> AnyHttpUrl:
        """Cognito user pool authorization url"""
        return f"{self.cognito_domain}/oauth2/authorize"

    @property
    def cognito_token_url(self) -> AnyHttpUrl:
        """Cognito user pool token and refresh url"""
        return f"{self.cognito_domain}/oauth2/token"

    @validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    def load_postgres_settings(self) -> "Settings":
        """Load postgres connection params from AWS secret"""

        if self.pgstac_secret_arn:
            secret = get_secret_dict(self.pgstac_secret_arn)

            return Settings(
                postgres_host_reader=secret["host"],
                postgres_host_writer=secret["host"],
                postgres_dbname=secret["dbname"],
                postgres_user=secret["username"],
                postgres_pass=secret["password"],
                postgres_port=secret["port"],
            )
        else:
            return Settings()

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_STAC_"


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


api_settings = ApiSettings()


class _TilesApiSettings(BaseSettings):
    """Tile API settings"""

    titiler_endpoint: Optional[str]

    class Config:
        """model config"""

        env_file = ".env"


@lru_cache()
def TilesApiSettings() -> _TilesApiSettings:
    """
    This function returns a cached instance of the TilesApiSettings object.
    Caching is used to prevent re-reading the environment every time the API settings are used in an endpoint.

    """
    return _TilesApiSettings()


extensions = [
    ContextExtension(),
    FieldsExtension(),
    FilterExtension(),
    QueryExtension(),
    SortExtension(),
    TokenPaginationExtension()
]

if api_settings.enable_transactions:
    extensions.extend(
        [
            BulkTransactionExtension(client=BulkTransactionsClient()),
            TransactionExtension(
                client=TransactionsClient(),
                settings=ApiSettings().load_postgres_settings(),
                response_class=ORJSONResponse,
            ),
        ]
    )
post_request_model = create_post_request_model(extensions, base_model=PgstacSearch)
get_request_model = create_get_request_model(extensions)
