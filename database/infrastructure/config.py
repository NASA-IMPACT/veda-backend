"""Veda-backend database construct configuration."""
from typing import Optional

from aws_cdk import aws_ec2, aws_rds
from pydantic import BaseSettings, Field


class vedaDBSettings(BaseSettings):
    """Application settings."""

    dbname: str = Field(
        "postgis",
        description="Name of postgres database",
    )
    admin_user: str = Field(
        "postgres",
        description="Name of admin role for postgres database",
    )
    user: str = Field(
        "veda",
        description="Name of pgstac role for postgres database",
    )
    pgstac_version: str = Field(
        ...,
        description="Version of PgStac database, i.e. 0.5",
    )
    schema_version: str = Field(
        ...,
        description="The version of the custom veda-backend schema, i.e. 0.1.1",
    )
    snapshot_id: Optional[str] = Field(
        None,
        description=(
            "RDS snapshot identifier to initialize RDS from a snapshot. "
            "**Once used always REQUIRED**"
        ),
    )
    publicly_accessible: Optional[bool] = Field(
        True, description="Boolean if the RDS should be publicly accessible"
    )
    # RDS custom postgres parameters
    max_locks_per_transaction: Optional[str] = Field(
        "1024",
        description="Number of database objects that can be locked simultaneously",
        regex=r"^[1-9]\d*$",
    )
    work_mem: Optional[str] = Field(
        "64000",
        description="Maximum amount of memory to be used by a query operation before writing to temporary disk files",
        regex=r"^[1-9]\d*$",
    )
    temp_buffers: Optional[str] = Field(
        "32000",
        description="maximum number of temporary buffers used by each session",
        regex=r"^[1-9]\d*$",
    )
    use_rds_proxy: Optional[bool] = Field(
        False,
        description="Boolean if the RDS should be accessed through a proxy",
    )
    rds_instance_class: Optional[str] = Field(
        aws_ec2.InstanceClass.BURSTABLE3.value,
        description=(
            "The instance class of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceClass.html"
        ),
    )
    rds_instance_size: Optional[str] = Field(
        aws_ec2.InstanceSize.SMALL.value,
        description=(
            "The size of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceSize.html"
        ),
    )
    rds_engine_full_version: Optional[str] = Field(
        aws_rds.PostgresEngineVersion.VER_14.postgres_full_version,
        description=(
            "The version of the RDS Postgres engine "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/PostgresEngineVersion.html"
        ),
    )
    rds_engine_major_version: Optional[str] = Field(
        aws_rds.PostgresEngineVersion.VER_14.postgres_major_version,
        description=(
            "The version of the RDS Postgres engine "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/PostgresEngineVersion.html"
        ),
    )
    rds_encryption: Optional[bool] = Field(
        False,
        description="Boolean if the RDS should be encrypted",
    )

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "VEDA_DB_"


veda_db_settings = vedaDBSettings()
