from typing import Dict, List, Optional

from pydantic import BaseSettings, Field


class FeatureLambdaSettings(BaseSettings):

    env: Dict = {}

    features_memory: int = 8192  # Mb

    features_timeout: int = 30  # seconds

    features_root_path: str = Field(
        "",
        description="Optional root path for all api endpoints",
    )

    custom_host: str = Field(
        None,
        description="Complete url of custom host including subdomain. When provided, override host in api integration",
    )

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "env_prefix": "VEDA_",
    }


features_lambda_settings = FeatureLambdaSettings()
