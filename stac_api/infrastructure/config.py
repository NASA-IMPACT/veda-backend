"""Configuration options for the Lambda backed API implementing `stac-fastapi`."""
from typing import Dict, Optional

from pydantic import BaseSettings, Field


class MyConfig(BaseSettings.Config):
    """Custom config class that support multiple env_prefixes"""

    @classmethod
    def prepare_field(cls, field) -> None:
        """Workaround to not overwrite ENV_PREFIX"""
        if "env_names" in field.field_info.extra:
            return
        return super().prepare_field(field)


class vedaSTACSettings(BaseSettings):
    """STAC settings"""

    env: Dict = {}

    timeout: int = 30  # seconds
    memory: int = 8000  # Mb

    # Secret database credentials
    pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    path_prefix: Optional[str] = Field(
        "",
        description="Optional path prefix to add to all api endpoints",
    )

    class Config(MyConfig):
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_STAC"


class Settings(vedaSTACSettings):
    """Application Settings"""

    host: Optional[str] = Field(
        "",
        description="Optional host to send to stac api",  # stac api populates the urls in the catalog based on this
    )

    class Config(MyConfig):
        "Model config"
        env_prefix = "VEDA_"


veda_stac_settings = Settings()
