"""Settings for Features API - any environment variables starting with
`VEDA_FEATURES_` will overwrite the values of variables in this file
"""

from typing import Dict

from pydantic import BaseSettings, Field


class FeatureLambdaSettings(BaseSettings):
    """settings that get loaded and bound to the Lambda service in /app.py"""

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

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"


features_lambda_settings = FeatureLambdaSettings()
