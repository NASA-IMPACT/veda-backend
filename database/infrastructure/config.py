"""Veda-backend database construct configuration."""

from typing import Optional

from aws_cdk import aws_ec2, aws_rds
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


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
    publicly_accessible: bool = Field(
        True, description="Boolean if the RDS should be publicly accessible"
    )
    # RDS custom postgres parameters
    max_locks_per_transaction: str = Field(
        "1024",
        description="Number of database objects that can be locked simultaneously",
        pattern=r"^[1-9]\d*$",
    )
    work_mem: str = Field(
        "64000",
        description="Maximum amount of memory to be used by a query operation before writing to temporary disk files",
        pattern=r"^[1-9]\d*$",
    )
    temp_buffers: str = Field(
        "32000",
        description="maximum number of temporary buffers used by each session",
        pattern=r"^[1-9]\d*$",
    )
    use_rds_proxy: Optional[bool] = Field(
        False,
        description="Boolean if the RDS should be accessed through a proxy",
    )
    proxy_max_connections_percent: int = Field(
        1,
        description=(
            "Percent of the instance's max_connections the RDS proxy may open. This "
            "is the admission control that bounds how many queries run at the "
            "database at once; the rest wait at the proxy instead of piling more "
            "work onto Postgres. The right value is a few concurrent queries per "
            "vCPU, not a share of max_connections, which is derived from instance "
            "memory and so says nothing about how many queries the instance can "
            "actually run at once--roughly 1,700 on a db.r5.large, whose real limit "
            "is two cores. On that instance 1 percent is about 10 connections, "
            "roughly 5 per vCPU, and it beat 2, 3 and 5 percent on every measure in "
            "a sweep: each query ran at its idle-time speed instead of contending, "
            "and the same request rate cost a third less CPU. Idle connections are "
            "held to the same percent so the pool stays warm, and because AWS "
            "requires the idle percent to be no greater than the max. Only used "
            "when use_rds_proxy is true"
        ),
        ge=1,
        le=100,
    )
    rds_instance_class: str = Field(
        aws_ec2.InstanceClass.BURSTABLE3.value,
        description=(
            "The instance class of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceClass.html"
        ),
        validate_default=True,
    )
    rds_instance_size: str = Field(
        aws_ec2.InstanceSize.SMALL.value,
        description=(
            "The size of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceSize.html"
        ),
        validate_default=True,
    )
    rds_engine_full_version: str = Field(
        aws_rds.PostgresEngineVersion.VER_14.postgres_full_version,
        description=(
            "The version of the RDS Postgres engine "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/PostgresEngineVersion.html"
        ),
    )
    rds_engine_major_version: str = Field(
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

    @field_validator("rds_instance_class", mode="before")
    def convert_rds_class_to_uppercase(cls, value):
        """Convert to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("rds_instance_size", mode="before")
    def convert_rds_size_to_uppercase(cls, value):
        """Convert to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "VEDA_DB_"
        extra = "ignore"


veda_db_settings = vedaDBSettings()
