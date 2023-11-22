"""App settings."""
from typing import Optional

from pydantic import BaseSettings, Field


class vedaAppSettings(BaseSettings):
    """Application settings."""

    # App name and deployment stage
    app_name: Optional[str] = Field(
        "veda-backend",
        description="Optional app name used to name stack and resources",
    )
    stage: str = Field(
        ...,
        description=(
            "Deployment stage used to name stack and resources, "
            "i.e. `dev`, `staging`, `prod`"
        ),
    )
    vpc_id: Optional[str] = Field(
        None,
        description=(
            "Resource identifier of VPC, if none a new VPC with public and private "
            "subnets will be provisioned."
        ),
    )
    cdk_default_account: Optional[str] = Field(
        None,
        description="When deploying from a local machine the AWS account id is required to deploy to an exiting VPC",
    )
    cdk_default_region: Optional[str] = Field(
        None,
        description="When deploying from a local machine the AWS region id is required to deploy to an exiting VPC",
    )
    permissions_boundary_policy_name: Optional[str] = Field(
        None,
        description="Name of IAM policy to define stack permissions boundary",
    )
    veda_domain_alt_hosted_zone_id: Optional[str] = Field(
        None,
        description="Route53 zone identifier if using a custom domain name",
    )
    veda_domain_alt_hosted_zone_name: Optional[str] = Field(
        None,
        description="Custom domain name, i.e. veda-backend.xyz",
    )

    bootstrap_qualifier: Optional[str] = Field(
        None,
        description="Custom bootstrap qualifier override if not using a default installation of AWS CDK Toolkit to synthesize app.",
    )

    def cdk_env(self) -> dict:
        """Load a cdk environment dict for stack"""

        if self.vpc_id:
            return {
                "account": self.cdk_default_account,
                "region": self.cdk_default_region,
            }
        else:
            return {}

    def alt_domain(self) -> bool:
        """True if alternative domain and host parameters provided"""
        return all(
            [
                self.veda_domain_alt_hosted_zone_id,
                self.veda_domain_alt_hosted_zone_name,
            ]
        )

    def stage_name(self) -> str:
        """Force lowercase stage name"""
        return self.stage.lower()

    class Config:
        """model config."""

        env_file = ".env"


veda_app_settings = vedaAppSettings()
