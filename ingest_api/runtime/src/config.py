from typing import Annotated

from pydantic import AnyHttpUrl, Field, StringConstraints
from pydantic_settings import BaseSettings

AwsArn = Annotated[str, StringConstraints(pattern=r"^arn:aws:iam::\d{12}:role/.+")]


class Settings(BaseSettings):
    dynamodb_table: str

    data_access_role_arn: AwsArn | None = Field(  # type: ignore
        None, description="ARN of AWS Role used to validate access to S3 data"
    )

    aws_request_payer: str | None = Field(
        None,
        description=(
            "Set optional global parameter to 'requester' "
            "if the requester agrees to pay S3 transfer costs"
        ),
    )

    stac_url: AnyHttpUrl = Field(description="URL of STAC API")
    root_path: str | None = None
    stage: str | None = Field(None, description="API stage")
    git_sha: str | None = Field(
        "", description="Git SHA of the deployed service"
    )  # default to str so that docker compose tests work

    keycloak_uma_resource_server_client_secret_name: str | None = Field(
        None,
        description=(
            "Name or ARN of the AWS Secrets Manager secret containing Keycloak UMA "
            "resource server client_id and client_secret. "
            "Use a full ARN for cross-account access."
        ),
    )


settings = Settings()
