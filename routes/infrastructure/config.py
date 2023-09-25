from pydantic import BaseSettings, Field, AnyHttpUrl
from typing import Optional


class vedaRouteSettings(BaseSettings):

    # S3 URLs
    stac_browser_bucket: str = Field(description="URL of the STAC browser")

    # API Gateway URLs
    ingest_url: AnyHttpUrl = Field(
        description="URL of ingest API",
    )

    domain_hosted_zone_name: Optional[str] = Field(
        None,
        description="Domain name for the cloudfront distribution",
    )

    domain_hosted_zone_id: Optional[str] = Field(
        None,
        description="Domain ID for the cloudfront distribution"
    )

    cert_arn: Optional[str] = Field(
        None,
        description="Certificate’s ARN",
    )

    using_mcp_acct: Optional[bool] = False

    class Config:
        env_prefix = "veda_"
        case_sentive = False
        env_file = ".env"

veda_route_settings = vedaRouteSettings()