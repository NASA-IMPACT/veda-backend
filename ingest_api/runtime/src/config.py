import os
from getpass import getuser
from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, Field, constr
from pydantic_ssm_settings import AwsSsmSourceConfig

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")


class Settings(BaseSettings):
    dynamodb_table: str

    jwks_url: Optional[AnyHttpUrl] = Field(
        description="URL of JWKS, e.g. https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json"  # noqa
    )
    authorization_url: AnyHttpUrl
    token_url: AnyHttpUrl
    refresh_url: AnyHttpUrl

    data_access_role_arn: AwsArn = Field(  # type: ignore
        description="ARN of AWS Role used to validate access to S3 data"
    )

    stac_url: AnyHttpUrl = Field(description="URL of STAC API")

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")

    client_id: str = Field(description="The Cognito APP client ID")
    client_secret: str = Field("", description="The Cognito APP client secret")
    root_path: Optional[str] = Field(description="Root path of API")
    stage: Optional[str] = Field(description="API stage")

    class Config(AwsSsmSourceConfig):
        env_file = ".env"

    @classmethod
    def from_ssm(cls, stack: str):
        return cls(_secrets_dir=f"/{stack}")


settings = (
    Settings(
        authorization_url="https://veda-auth-stack-test.auth.us-west-2.amazoncognito.com/oauth2/authorize",
        token_url=f"https://veda-auth-stack-test.auth.us-west-2.amazoncognito.com/oauth2/token",
        refresh_url=f"https://veda-auth-stack-test.auth.us-west-2.amazoncognito.com/oauth2/token",
    )
    if os.environ.get("NO_PYDANTIC_SSM_SETTINGS")
    else Settings.from_ssm(
        stack=os.environ.get(
            "STACK", f"veda-stac-ingestion-system-{os.environ.get('STAGE', getuser())}"
        ),
    )
)
