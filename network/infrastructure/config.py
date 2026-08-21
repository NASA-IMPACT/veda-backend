"""Configuration options for the VPC."""

from pydantic_settings import BaseSettings


# https://medium.com/aws-activate-startup-blog/practical-vpc-design-8412e1a18dcc#.bmeh8m3si
# https://www.admin-magazine.com/Articles/The-AWS-CDK-for-software-defined-deployments/(offset)/6
class BaseVpcSettings(BaseSettings):
    """Base VPC settings"""

    cidr: str
    max_azs: int = 2
    nat_gateways: int = 1
    public_mask: int = 24
    private_mask: int = 24


class devVpcSettings(BaseVpcSettings):
    """Dev VPC settings"""

    cidr: str = "10.100.0.0/16"


class stagingVpcSettings(BaseVpcSettings):
    """Staging VPC settings"""

    env: dict = {}
    cidr: str = "10.200.0.0/16"


class prodVpcSettings(BaseVpcSettings):
    """Production VPC settings"""

    env: dict = {}
    cidr: str = "10.40.0.0/16"


dev_vpc_settings = devVpcSettings()
staging_vpc_settings = stagingVpcSettings()
prod_vpc_settings = prodVpcSettings()
