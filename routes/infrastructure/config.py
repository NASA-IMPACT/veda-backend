"""Settings for Cloudfront distribution - any environment variables starting with
`VEDA_` will overwrite the values of variables in this file
"""
from typing import Optional

from pydantic import BaseSettings, Field


class vedaRouteSettings(BaseSettings):
    """Veda Route settings"""

    cloudfront: Optional[bool] = Field(
        False,
        description="Boolean if Cloudfront Distribution should be deployed",
    )

    # STAC S3 browser bucket name
    stac_browser_bucket: Optional[str] = Field(
        None, description="STAC browser S3 bucket name"
    )

    # API Gateway URLs
    ingest_url: Optional[str] = Field(
        "",
        description="URL of ingest API",
    )

    domain_hosted_zone_name: Optional[str] = Field(
        None,
        description="Domain name for the cloudfront distribution",
    )

    domain_hosted_zone_id: Optional[str] = Field(
        None, description="Domain ID for the cloudfront distribution"
    )

    cert_arn: Optional[str] = Field(
        None,
        description="Certificate’s ARN",
    )

    class Config:
        """model config"""

        env_prefix = "VEDA_"
        case_sentive = False
        env_file = ".env"


veda_route_settings = vedaRouteSettings()
