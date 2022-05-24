"""App settings."""
from typing import Optional

import pydantic


class deltaAppSettings(pydantic.BaseSettings):
    """Application settings."""

    # App name and deployment stage
    app_name: Optional[str] = "delta-backend"
    stage: str

    # Optional specify vpc-id in target account
    vpc_id: Optional[str] = None
    cdk_default_account: Optional[str] = None
    cdk_default_region: Optional[str] = None

    # Optional permissions boundary policy
    permissions_boundary_policy: Optional[str] = None

    def cdk_env(self) -> dict:
        """Load a cdk environment dict for stack"""

        if self.vpc_id:
            return {
                "account": self.cdk_default_account,
                "region": self.cdk_default_region,
            }
        else:
            return {}

    class Config:
        """model config."""

        env_file = ".env"


delta_app_settings = deltaAppSettings()
