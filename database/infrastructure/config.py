"""Delta-backend database construct configuration."""
from typing import Optional

from pydantic import BaseSettings, Field


class deltaDBSettings(BaseSettings):
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
        "delta",
        description="Name of pgstac role for postgres database",
    )
    pgstac_version: str = Field(
        ...,
        description="Version of PgStac database, i.e. 0.5",
    )
    schema_version: str = Field(
        ...,
        description="The version of the custom delta-backend schema, i.e. 0.1.1",
    )
    snapshot_id: Optional[str] = Field(
        None,
        description=(
            "RDS snapshot identifier to initialize RDS from a snapshot. "
            "**Once used always REQUIRED**"
        ),
    )
    private_subnets: Optional[bool] = Field(
        False,
        description="Boolean deploy database to private subnets",
    )

    # RDS custom postgres parameters
    max_locks_per_transaction: Optional[str] = Field(
        "1024",
        description="Number of database objects that can be locked simultaneously",
        regex="^[1-9]\d*$",
    )
    work_mem: Optional[str] = Field(
        "64000",
        description="Maximum amount of memory to be used by a query operation before writing to temporary disk files",
        regex="^[1-9]\d*$",
    )
    temp_buffers: Optional[str] = Field(
        "32000", 
        description="maximum number of temporary buffers used by each session"
        regex="^[1-9]\d*$",
    )

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "DELTA_DB_"


delta_db_settings = deltaDBSettings()
