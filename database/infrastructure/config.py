import pydantic


class deltaDBSettings(pydantic.BaseSettings):
    """Application settings"""

    dbname: str = "postgis"
    user: str = "eostac"

    # Define PGSTAC VERSION
    pgstac_version: str

    class Config:
        """model config"""

        env_file = "deployment/.env"
        env_prefix = "DELTA_DB_"


delta_db_settings = deltaDBSettings()
