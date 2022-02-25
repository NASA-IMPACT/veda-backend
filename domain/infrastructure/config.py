import pydantic


class deltaDomainSettings(pydantic.BaseSettings):
    """Application settings"""

    hosted_zone_id: str = None
    hosted_zone_name: str = None

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "DELTA_DOMAIN_"


delta_domain_settings = deltaDomainSettings()
