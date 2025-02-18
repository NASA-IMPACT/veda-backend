"""Configuration options for the Lambda backed API implementing `stac-fastapi`."""

from typing import Dict, Optional

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings


class vedaSTACSettings(BaseSettings):
    """Application settings"""

    env: Dict = {}

    timeout: int = 30  # seconds
    memory: int = 8000  # Mb

    # Secret database credentials
    stac_pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    stac_root_path: str = Field(
        "",
        description="Optional path prefix to add to all api endpoints",
    )

    raster_root_path: str = Field(
        "",
        description="Optional path prefix to add to all raster endpoints",
    )

    custom_host: str = Field(
        None,
        description="Complete url of custom host including subdomain. When provided, override host in api integration",
    )

    project_name: Optional[str] = Field(
        "VEDA (Visualization, Exploration, and Data Analysis)",
        description="Name of the STAC Catalog",
    )

    project_description: Optional[str] = Field(
        "VEDA (Visualization, Exploration, and Data Analysis) is NASA's open-source Earth Science platform in the cloud.",
        description="Description of the STAC Catalog",
    )

    userpool_id: Optional[str] = Field(
        None, description="The Cognito Userpool used for authentication"
    )
    cognito_domain: Optional[AnyHttpUrl] = Field(
        None,
        description="The base url of the Cognito domain for authorization and token urls",
    )
    client_id: Optional[str] = Field(None, description="The Cognito APP client ID")
    client_secret: Optional[str] = Field(
        "", description="The Cognito APP client secret"
    )
    stac_enable_transactions: bool = Field(
        False, description="Whether to enable transactions endpoints"
    )
    disable_default_apigw_endpoint: Optional[bool] = Field(
        False,
        description="Boolean to disable default API gateway endpoints for stac, raster, and ingest APIs. Defaults to false.",
    )

    @model_validator(mode="before")
    def check_transaction_fields(cls, values):
        """
        Validates the existence of auth env vars in case stac_enable_transactions is True
        """
        if values.get("stac_enable_transactions"):
            missing_fields = [
                field
                for field in ["userpool_id", "cognito_domain", "client_id"]
                if not values.get(field)
            ]
            if missing_fields:
                raise ValueError(
                    f"When 'stac_enable_transactions' is True, the following fields must be provided: {', '.join(missing_fields)}"
                )
        return values

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"
        extra = "ignore"


veda_stac_settings = vedaSTACSettings()
