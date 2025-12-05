"""Settings for EC2 Instance."""
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Ec2InstanceSettings(BaseSettings):
    """Application settings for EC2 Instance."""

    instance_type_class: str = Field(
        "T3",
        description="EC2 instance class",
    )

    instance_type_size: str = Field(
        "MICRO",
        description="EC2 instance size",
    )

    key_pair_name: Optional[str] = Field(
        None,
        description="Name of existing EC2 Key Pair for SSH access but it is optional, Session Manager is enabled by default",
    )

    enable_database_access: bool = Field(
        True,
        description="Enable security group rules to allow EC2 to connect to databases",
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"
        extra = "ignore"


ec2_instance_settings = Ec2InstanceSettings()
