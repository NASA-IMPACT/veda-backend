"""Configuration options for the VPC."""
from typing import Dict

from pydantic import BaseSettings


# https://medium.com/aws-activate-startup-blog/practical-vpc-design-8412e1a18dcc#.bmeh8m3si
# https://www.admin-magazine.com/Articles/The-AWS-CDK-for-software-defined-deployments/(offset)/6
class devVpcSettings(BaseSettings):
    """Dev VPC settings"""

    cidr: str = "10.100.0.0/16"
    max_azs: int = 2
    nat_gateways: int = 1
    public_mask: int = 24
    private_mask: int = 24


class stagingVpcSettings(BaseSettings):
    """Staging VPC settings"""

    env: Dict = {}
    cidr: str = "10.200.0.0/16"
    max_azs: int = 2
    nat_gateways: int = 1
    public_mask: int = 24
    private_mask: int = 24


class prodVpcSettings(BaseSettings):
    """Production VPC settings"""

    env: Dict = {}
    cidr: str = "10.40.0.0/16"
    max_azs: int = 2
    nat_gateways: int = 1
    public_mask: int = 24
    private_mask: int = 24


dev_vpc_settings = devVpcSettings()
staging_vpc_settings = stagingVpcSettings()
prod_vpc_settings = prodVpcSettings()
