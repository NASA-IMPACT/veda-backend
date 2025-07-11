"""App settings."""
from getpass import getuser
from typing import List, Optional

from pydantic import Field, constr
from pydantic_settings import BaseSettings

AwsSubnetId = constr(pattern=r"^subnet-[a-z0-9]{17}$")


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
    owner: str = Field(
        description=" ".join(
            [
                "Name of primary contact for Cloudformation Stack.",
                "Used to tag generated resources",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )

    vpc_id: Optional[str] = Field(
        None,
        description=(
            "Resource identifier of VPC, if none a new VPC with public and private "
            "subnets will be provisioned."
        ),
    )
    subnet_ids: Optional[List[AwsSubnetId]] = Field(  # type: ignore
        [],
        description="The subnet ids of subnets associated with the VPC to be used for the database and lambda function.",
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

    stac_browser_tag: Optional[str] = Field(
        "v3.1.0",
        description=(
            "Tag of the radiant earth stac-browser repo to use to build the app"
            "https://github.com/radiantearth/stac-browser/releases."
        ),
    )

    cloudfront: Optional[bool] = Field(
        False,
        description="Boolean if Cloudfront Distribution should be deployed",
    )

    veda_custom_host: Optional[str] = Field(
        None,
        description="Complete url of custom host including subdomain. Used to infer url of stac-api before app synthesis.",
    )

    veda_stac_root_path: str = Field(
        "",
        description="STAC API root path. Used to infer url of stac-api before app synthesis.",
    )

    veda_raster_root_path: str = Field(
        "",
        description="Raster API root path",
    )

    veda_domain_create_custom_subdomains: bool = Field(
        False,
        description=(
            "When true and hosted zone config is provided, create a unique subdomain for stac and raster apis. "
            "For example <stage>-stac.<hosted_zone_name> and <stage>-raster.<hosted_zone_name>"
        ),
    )
    veda_domain_hosted_zone_name: Optional[str] = Field(
        None, description="Custom domain name, i.e. veda-backend.xyz"
    )

    disable_default_apigw_endpoint: Optional[bool] = Field(
        False,
        description="Boolean to disable default API gateway endpoints for stac, raster, and ingest APIs. Defaults to false.",
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

    def stage_name(self) -> str:
        """Force lowercase stage name"""
        return self.stage.lower()

    def get_stac_catalog_url(self) -> Optional[str]:
        """Infer stac catalog url based on whether the app is configured to deploy the catalog to a custom subdomain or to a cloudfront route"""
        if self.veda_custom_host and self.veda_stac_root_path:
            return f"https://{veda_app_settings.veda_custom_host}{veda_app_settings.veda_stac_root_path}"
        if (
            self.veda_domain_create_custom_subdomains
            and self.veda_domain_hosted_zone_name
        ):
            return (
                f"https://{self.stage.lower()}-stac.{self.veda_domain_hosted_zone_name}"
            )
        return None

    class Config:
        """model config."""

        env_file = ".env"
        extra = "ignore"


veda_app_settings = vedaAppSettings()
