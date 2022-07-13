"""Configuration options for the Lambda backed API implementing `stac-fastapi`."""
from typing import Dict, Optional

from pydantic import BaseSettings, Field


class deltaSTACSettings(BaseSettings):
    """Application settings"""

    env: Dict = {}

    timeout: int = 60 * 2  # seconds
    memory: int = 256  # Mb

    # Secret database credentials
    pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_STAC_"


delta_stac_settings = deltaSTACSettings()
