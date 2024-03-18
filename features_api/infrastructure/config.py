from typing import Dict, List, Optional

from pydantic import BaseSettings, Field


class FeatureSettings(BaseSettings):
    """Application settings"""

    # seconds until collections get refreshed from DB
    features_catalog_ttl: int = 300  # seconds

    timeout: int = 30  # seconds

    memory: int = 8000  # Mb

    features_pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    features_root_path: str = Field(
        "",
        description="Optional root path for all api endpoints",
    )

    features_host: str = Field(
        None,
        description="Complete url of custom host including subdomain. When provided, override host in api integration",
    )

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "env_prefix": "VEDA_",
    }


features_api_settings = FeaturesSettings()
