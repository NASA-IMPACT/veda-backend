"""Delta-backend database construct configuration."""
from typing import Optional
import pydantic


class deltaDBSettings(pydantic.BaseSettings):
    """Application settings."""

    dbname: str = "postgis"
    admin_user: str = "postgres"
    user: str = "delta"

    # Define PGSTAC VERSION
    pgstac_version: str

    # Dashboard schema version
    schema_version: str

    # Optional snapshot id to restore
    snapshot_id: Optional[str] = None

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "DELTA_DB_"


delta_db_settings = deltaDBSettings()
