from typing import Optional

from pydantic import AnyHttpUrl, Field, StringConstraints
from pydantic_settings import BaseSettings
from typing_extensions import Annotated

AwsArn = Annotated[str, StringConstraints(pattern=r"^arn:aws:iam::\d{12}:role/.+")]


class Settings(BaseSettings):
    dynamodb_table: str

    data_access_role_arn: Optional[AwsArn] = Field(  # type: ignore
        None, description="ARN of AWS Role used to validate access to S3 data"
    )

    aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    stac_url: AnyHttpUrl = Field(description="URL of STAC API")
    root_path: Optional[str] = None
    stage: Optional[str] = Field(None, description="API stage")
    git_sha: Optional[str] = Field(
        "", description="Git SHA of the deployed service"
    )  # default to str so that docker compose tests work

    keycloak_uma_resource_server_client_secret_name: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secrets Manager secret containing Keycloak UMA resource server client_id and client_secret. Use a full ARN for cross-account access.",
    )
    tenant_filter_field: str = Field(
        "eic:tenant",
        description="Collection field name used to resolve tenant ownership."
    )


settings = Settings()
