"""Configuration options for a custom API domain."""

from typing import Optional

from pydantic import BaseSettings, Field


class vedaDomainSettings(BaseSettings):
    """Application settings"""

    hosted_zone_id: Optional[str] = Field(
        None, description="Route53 hosted zone identifier if using a custom domain name"
    )
    hosted_zone_name: Optional[str] = Field(
        None, description="Custom domain name, i.e. veda-backend.xyz"
    )
    create_custom_subdomains: bool = Field(
        False,
        description=(
            "When true and hosted zone config is provided, create a unique subdomain for stac and raster apis. "
            "For example <stage>-stac.<hosted_zone_name> and <stage>-raster.<hosted_zone_name>"
        ),
    )
    api_prefix: Optional[str] = Field(
        None,
        description=(
            "Domain prefix override supports using a custom prefix instead of the "
            "STAGE variabe (an alternate version of the stack can be deployed with a "
            "unique STAGE=altprod and after testing prod API traffic can be cut over "
            "to the alternate version of the stack by setting the prefix to prod)"
        ),
    )

    # Temporary support for deploying APIs to a second custom domain
    alt_hosted_zone_id: Optional[str] = Field(
        None, description="Second Route53 zone identifier if using a custom domain name"
    )
    alt_hosted_zone_name: Optional[str] = Field(
        None, description="Second custom domain name, i.e. alt-veda-backend.xyz"
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_DOMAIN_"


veda_domain_settings = vedaDomainSettings()
