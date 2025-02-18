from typing import Optional

from pydantic import AnyHttpUrl, ConfigDict, Field, StringConstraints
from pydantic_settings import BaseSettings
from typing_extensions import Annotated
from veda_auth import VedaAuth

AwsArn = Annotated[str, StringConstraints(pattern=r"^arn:aws:iam::\d{12}:role/.+")]


class Settings(BaseSettings):
    dynamodb_table: str

    jwks_url: Optional[AnyHttpUrl] = Field(
        None,
        description="URL of JWKS, e.g. https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json",  # noqa
    )

    data_access_role_arn: Optional[AwsArn] = Field(  # type: ignore
        None, description="ARN of AWS Role used to validate access to S3 data"
    )

    aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    stac_url: AnyHttpUrl = Field(description="URL of STAC API")

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")

    cognito_domain: Optional[AnyHttpUrl] = Field(
        None,
        description="The base url of the Cognito domain for authorization and token urls",
    )
    client_id: str = Field(None, description="The Cognito APP client ID")
    client_secret: str = Field("", description="The Cognito APP client secret")
    root_path: Optional[str] = None
    stage: Optional[str] = Field(None, description="API stage")

    @property
    def cognito_authorization_url(self) -> AnyHttpUrl:
        """Cognito user pool authorization url"""
        return f"{self.cognito_domain}/oauth2/authorize"

    @property
    def cognito_token_url(self) -> AnyHttpUrl:
        """Cognito user pool token and refresh url"""
        return f"{self.cognito_domain}/oauth2/token"

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

auth = VedaAuth(settings)
