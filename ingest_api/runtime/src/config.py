import os
from getpass import getuser
from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, Field, constr
from pydantic_ssm_settings import AwsSsmSourceConfig

from veda_auth import VedaAuth

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")


class Settings(BaseSettings):
    dynamodb_table: str

    jwks_url: Optional[AnyHttpUrl] = Field(
        description="URL of JWKS, e.g. https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json"  # noqa
    )

    data_access_role_arn: Optional[AwsArn] = Field(  # type: ignore
        description="ARN of AWS Role used to validate access to S3 data"
    )

    aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    stac_url: AnyHttpUrl = Field(description="URL of STAC API")

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")

    cognito_domain: Optional[AnyHttpUrl] = Field(
        description="The base url of the Cognito domain for authorization and token urls"
    )
    client_id: str = Field(description="The Cognito APP client ID")
    client_secret: str = Field("", description="The Cognito APP client secret")
    root_path: Optional[str] = None
    stage: Optional[str] = Field(description="API stage")

    @property
    def cognito_authorization_url(self) -> AnyHttpUrl:
        """Cognito user pool authorization url"""
        return f"{self.cognito_domain}/oauth2/authorize"

    @property
    def cognito_token_url(self) -> AnyHttpUrl:
        """Cognito user pool token and refresh url"""
        return f"{self.cognito_domain}/oauth2/token"

    class Config(AwsSsmSourceConfig):
        env_file = ".env"

    @classmethod
    def from_ssm(cls, stack: str):
        return cls(_secrets_dir=f"/{stack}")


settings = (
    Settings()
    if os.environ.get("NO_PYDANTIC_SSM_SETTINGS")
    else Settings.from_ssm(
        stack=os.environ.get(
            "STACK", f"veda-stac-ingestion-system-{os.environ.get('STAGE', getuser())}"
        ),
    )
)

auth = VedaAuth(settings)
