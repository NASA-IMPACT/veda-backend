"""Settings for Raster API - any environment variables starting with
`VEDA_RASTER_` will overwrite the values of variables in this file
"""

import subprocess
from typing import Dict, List, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class vedaRasterSettings(BaseSettings):
    """Application settings"""

    # Default options are optimized for CloudOptimized GeoTIFF
    # For more information on GDAL env see: https://gdal.org/user/configoptions.html
    # or https://developmentseed.org/titiler/advanced/performance_tuning/
    env: Dict = {
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff",
        "GDAL_CACHEMAX": "200",  # 200 mb
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "GDAL_INGESTED_BYTES_AT_OPEN": "32768",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MULTIPLEX": "YES",
        "GDAL_HTTP_VERSION": "2",
        "GDAL_HTTP_MAX_RETRY": "5",
        "GDAL_HTTP_RETRY_DELAY": "0.42685866976877296",
        "PYTHONWARNINGS": "ignore",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": "5000000",  # 5 MB (per file-handle)
        "RIO_TILER_MAX_THREADS": "1",
        "DB_MIN_CONN_SIZE": "1",
        "DB_MAX_CONN_SIZE": "1",
        # "CPL_DEBUG": "ON",
        # "CPL_CURL_VERBOSE": "TRUE",
        "CPL_VSIL_CURL_CHUNK_SIZE": "81920",
    }

    # S3 bucket names where TiTiler could do HEAD and GET Requests
    # specific private and public buckets MUST be added if you want to use s3:// urls
    # You can whitelist all bucket by setting `*`.
    # ref: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html
    buckets: List = ["*"]

    # S3 key pattern to limit the access to specific items (e.g: "my_data/*.tif")
    key: str = "*"

    timeout: int = 30  # seconds
    memory: int = 8000  # Mb

    raster_enable_mosaic_search: bool = Field(
        False,
        description="Deploy the raster API with the mosaic/list endpoint TRUE/FALSE",
    )
    raster_statement_timeout: str = Field(
        "28s",
        description=(
            "Maximum duration of a single query issued by the raster API, applied as "
            "a startup option on the connections this Lambda opens, so it binds only "
            "this service and leaves ingest and ad-hoc sessions alone. It must be "
            "shorter than the Lambda timeout: otherwise the invocation is killed "
            "first and Postgres keeps working on a query whose caller is already "
            "gone, which is what turned a traffic spike into a database death "
            "spiral. Needs an explicit unit, e.g. 500ms, 28s, 5min"
        ),
        pattern=r"^\d+(ms|s|min|h|d)$",
    )
    raster_reserved_concurrency: Optional[int] = Field(
        None,
        description=(
            "Optional reserved concurrency for the raster API lambda. This is a "
            "backstop, not the primary control: the proxy connection cap is what "
            "protects the database, but under sustained overload the raster fleet "
            "still grows toward the account's unreserved concurrency pool, which "
            "every other function in the account shares. This reservation exists so "
            "a raster runaway cannot starve them. Set it well above what real "
            "browser traffic needs and below the account's concurrency limit. Unset "
            "by default because the right number depends on the account"
        ),
        ge=1,
    )
    raster_pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    raster_data_access_role_arn: Optional[str] = Field(
        None,
        description="Resource name of role permitting access to specified external S3 buckets",
    )

    raster_export_assume_role_creds_as_envs: Optional[bool] = Field(
        False,
        description="enables 'get_gdal_config' flow to export AWS credentials as os env vars",
    )

    raster_aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    raster_root_path: str = Field(
        "",
        description="Optional root path for all api endpoints",
    )

    custom_host: Optional[str] = Field(
        None,
        description="Complete url of custom host including subdomain. When provided, override host in api integration",
    )

    project_name: str = Field(
        "VEDA (Visualization, Exploration, and Data Analysis)",
        description="Name of the STAC Catalog",
    )
    disable_default_apigw_endpoint: Optional[bool] = Field(
        False,
        description="Boolean to disable default API gateway endpoints for stac, raster, and ingest APIs. Defaults to false.",
    )

    git_sha: str = Field(
        subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("utf-8"),
        description="Git SHA of the current commit, used to track deployment version",
    )

    @field_validator("raster_statement_timeout")
    @classmethod
    def timeout_shorter_than_lambda(cls, value: str, info: ValidationInfo) -> str:
        """Require the query to be cancelled before the invocation is killed."""
        lambda_timeout = info.data.get("timeout")
        if lambda_timeout is None:
            return value

        unit = value.lstrip("0123456789")
        scale = {"ms": 0.001, "s": 1, "min": 60, "h": 3600, "d": 86400}[unit]
        seconds = int(value[: len(value) - len(unit)]) * scale
        if seconds >= lambda_timeout:
            raise ValueError(
                f"raster_statement_timeout ({value}) must be shorter than the raster "
                f"Lambda timeout ({lambda_timeout}s), so Postgres cancels the query "
                "before Lambda kills the invocation"
            )
        return value

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_"
        extra = "ignore"


veda_raster_settings = vedaRasterSettings()
