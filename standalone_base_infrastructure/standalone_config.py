"""Configuration options for optional stand-alone VPC Stack"""

from pydantic import Field
from pydantic_settings import BaseSettings


class baseSettings(BaseSettings):
    """Settings for standalone base infrastructure"""

    base_name: str | None = Field(
        "veda-shared",
        description="Optional name used to name stack and resources",
    )
    cdk_default_account: str | None = Field(
        None,
        description=(
            "When deploying from a local machine the AWS account id "
            "is required to deploy to an exiting VPC"
        ),
    )
    cdk_default_region: str | None = Field(
        None,
        description=(
            "When deploying from a local machine the AWS region id "
            "is required to deploy to an exiting VPC"
        ),
    )

    vpc_cidr: str | None = "10.100.0.0/16"
    vpc_max_azs: int | None = 2
    vpc_nat_gateways: int | None = 1

    def cdk_env(self) -> dict:
        """Load a cdk environment dict for stack"""
        return {
            "account": self.cdk_default_account,
            "region": self.cdk_default_region,
        }

    class Config:
        """model config."""

        env_file = ".env"


base_settings = baseSettings()
