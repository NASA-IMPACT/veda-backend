"""Delta-backend database construct configuration."""
import pydantic


class deltaDBSettings(pydantic.BaseSettings):
    """Application settings."""

    dbname: str = "postgis"
    user: str = "delta"

    # Define PGSTAC VERSION
    pgstac_version: str
    # Define delta db/custom schema version
    version: str

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "DELTA_DB_"


delta_db_settings = deltaDBSettings()
