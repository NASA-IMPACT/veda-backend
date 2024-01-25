from pydantic import AnyHttpUrl, BaseSettings, Field, constr
from pydantic_ssm_settings import AwsSsmSourceConfig

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")
AwsStepArn = constr(regex=r"^arn:aws:states:.+:\d{12}:stateMachine:.+")


class Settings(BaseSettings):
    dynamodb_table: str

    jwks_url: AnyHttpUrl = Field(
        description="URL of JWKS, e.g. https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json"  # noqa
    )

    data_access_role_arn: AwsArn = Field(  # type: ignore
        description="ARN of AWS Role used to validate access to S3 data"
    )

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")

    client_id: str = Field(description="The Cognito APP client ID")
    client_secret: str = Field("", description="The Cognito APP client secret")
    ingest_root_path: str = Field(description="Root path of API")
    stage: str = Field(description="API stage")
    workflow_root_path: str = Field(description="Root path of API")

    class Config(AwsSsmSourceConfig):
        env_file = ".env"

    @classmethod
    def from_ssm(cls, stack: str):
        return cls(_secrets_dir=f"/{stack}")
