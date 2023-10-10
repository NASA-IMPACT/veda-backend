"""Settings for Raster API - any environment variables starting with
`VEDA_RASTER_` will overwrite the values of variables in this file
"""
from typing import Dict, List, Optional

from pydantic import BaseSettings, Field


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

    enable_mosaic_search: bool = Field(
        False,
        description="Deploy the raster API with the mosaic/list endpoint TRUE/FALSE",
    )
    pgstac_secret_arn: Optional[str] = Field(
        None,
        description="Name or ARN of the AWS Secret containing database connection parameters",
    )

    data_access_role_arn: Optional[str] = Field(
        None,
        description="Resource name of role permitting access to specified external S3 buckets",
    )

    export_assume_role_creds_as_envs: Optional[bool] = Field(
        False,
        description="enables 'get_gdal_config' flow to export AWS credentials as os env vars",
    )

    aws_request_payer: Optional[str] = Field(
        None,
        description="Set optional global parameter to 'requester' if the requester agrees to pay S3 transfer costs",
    )

    path_prefix: Optional[str] = Field(
        "",
        description="Optional path prefix to add to all api endpoints",
    )

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_RASTER_"


veda_raster_settings = vedaRasterSettings()
