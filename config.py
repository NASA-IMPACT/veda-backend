"""App settings."""
from getpass import getuser
from typing import Optional

from pydantic import BaseSettings, Field, constr

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")
AwsStepArn = constr(regex=r"^arn:aws:states:.+:\d{12}:stateMachine:.+")
AwsOidcArn = constr(regex=r"^arn:aws:iam::\d{12}:oidc-provider/.+")


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

    veda_custom_host: str = Field(
        None,
        description="Complete url of custom host including subdomain. Used to infer url of stac-api before app synthesis.",
    )

    veda_stac_root_path: str = Field(
        "",
        description="Optional path prefix to add to all api endpoints. Used to infer url of stac-api before app synthesis.",
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

    def get_stac_catalog_url(self) -> Optional[str]:
        """Infer stac catalog url based on whether the app is configured to deploy the catalog to a custom subdomain or to a cloudfront route"""
        if self.veda_custom_host and self.veda_stac_root_path:
            return f"https://{veda_app_settings.veda_custom_host}/{veda_app_settings.veda_stac_root_path.lstrip('/')}"
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


veda_app_settings = vedaAppSettings()
