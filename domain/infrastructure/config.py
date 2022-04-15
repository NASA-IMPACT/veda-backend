"""Configuration options for a custom API domain."""
# TODO: make the domain root (`delta-backend.xyz` configurable too)
from typing import Optional

import pydantic


class deltaDomainSettings(pydantic.BaseSettings):
    """Application settings"""

    hosted_zone_id: Optional[str] = None
    hosted_zone_name: Optional[str] = None
    api_prefix: Optional[str] = None

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_DOMAIN_"


delta_domain_settings = deltaDomainSettings()
