"""Configuration options for the Lambda backed API implementing `stac-fastapi`."""
from typing import Dict, Optional

from pydantic import BaseSettings, Field


class vedaSTACSettings(BaseSettings):
    """Application settings"""

    env: Dict = {}

    timeout: int = 30  # seconds
    memory: int = 8000  # Mb

    # Secret database credentials
    pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    path_prefix: Optional[str] = Field(
        None,
        description="Optional path prefix to add to all api endpoints",
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_STAC_"


veda_stac_settings = vedaSTACSettings()
