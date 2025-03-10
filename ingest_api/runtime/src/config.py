from typing import Optional

from pydantic import AnyHttpUrl, ConfigDict, Field, StringConstraints
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

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
