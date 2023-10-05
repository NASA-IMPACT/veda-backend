"""Configuration options for a custom API domain."""

from typing import Optional

from pydantic import BaseSettings, Field


class vedaDomainSettings(BaseSettings):
    """Application settings"""

    domain_hosted_zone_id: Optional[str] = Field(
        None, description="Route53 hosted zone identifier if using a custom domain name"
    )
    domain_hosted_zone_name: Optional[str] = Field(
        None, description="Custom domain name, i.e. veda-backend.xyz"
    )

    stac_path_prefix: Optional[str] = Field(
        "",
        description="Optional path prefix to add to all api endpoints",
    )

    raster_path_prefix: Optional[str] = Field(
        "",
        description="Optional path prefix to add to all api endpoints",
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

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"


veda_domain_settings = vedaDomainSettings()
