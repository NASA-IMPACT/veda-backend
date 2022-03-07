"""Configuration options for the Lambda backed API implementing `stac-fastapi`."""
from typing import Dict

import pydantic


class deltaSTACSettings(pydantic.BaseSettings):
    """Application settings"""

    env: Dict = {}

    timeout: int = 60 * 2  # seconds
    memory: int = 256  # Mb

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_STAC_"


delta_stac_settings = deltaSTACSettings()
