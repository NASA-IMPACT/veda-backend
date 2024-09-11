"""Settings for getting or creating S3 static website for both a stac-browser and for optional cloudfront origin.
Any environment variables starting with `VEDA_` will overwrite the values of variables in this file
"""
from typing import Optional

from pydantic.v1.env_settings import BaseSettings
from pydantic.v1.fields import Field


class vedaS3WebsiteSettings(BaseSettings):
    """Application settings"""

    stac_browser_bucket: Optional[str] = Field(
        None,
        description=(
            "Optional existing bucket provisioned as public website"
            "If not provided, a new bucket will be created and configured"
        ),
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"


veda_s3_website_settings = vedaS3WebsiteSettings()
