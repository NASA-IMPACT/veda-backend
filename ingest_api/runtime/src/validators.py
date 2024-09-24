import functools
from typing import Union

import boto3
import requests


@functools.lru_cache
def get_s3_credentials():
    from src.main import settings

    if not settings.data_access_role_arn:
        return {}

    print("Fetching S3 Credentials...")
    response = boto3.client("sts").assume_role(
        RoleArn=settings.data_access_role_arn,
        RoleSessionName="stac-ingestor-data-validation",
    )
    return {
        "aws_access_key_id": response["Credentials"]["AccessKeyId"],
        "aws_secret_access_key": response["Credentials"]["SecretAccessKey"],
        "aws_session_token": response["Credentials"]["SessionToken"],
    }


def s3_object_is_accessible(bucket: str, key: str):
    """
    Ensure we can send HEAD requests to S3 objects.
    """
    from src.main import settings

    client = boto3.client("s3", **get_s3_credentials())
    try:
        if settings.aws_request_payer:
            client.head_object(
                Bucket=bucket, Key=key, RequestPayer=settings.aws_request_payer
            )
        else:
            client.head_object(Bucket=bucket, Key=key)
    except client.exceptions.ClientError as e:
        raise ValueError(
            f"Asset not accessible: {e.__dict__['response']['Error']['Message']}"
        )


@functools.lru_cache
def s3_bucket_object_is_accessible(
    bucket: str, prefix: str, zarr_store: Union[str, None] = None
):
    """
    Ensure we can send HEAD requests to S3 objects in bucket.
    """
    client = boto3.client("s3", **get_s3_credentials())
    prefix = f"{prefix}{zarr_store}" if zarr_store else prefix
    try:
        result = client.list_objects(Bucket=bucket, Prefix=prefix, MaxKeys=2)
    except client.exceptions.NoSuchBucket:
        raise ValueError("Bucket doesn't exist.")
    except client.exceptions.ClientError as e:
        raise ValueError(f"Access denied: {e.__dict__['response']['Error']['Message']}")
    content = result.get("Contents", [])
    if len(content) < 1:
        raise ValueError("No data in bucket/prefix.")
    try:
        client.head_object(Bucket=bucket, Key=content[0].get("Key"))
    except client.exceptions.ClientError as e:
        raise ValueError(
            f"Asset not accessible: {e.__dict__['response']['Error']['Message']}"
        )


def url_is_accessible(href: str):
    """
    Ensure URLs are accessible via HEAD requests.
    """
    try:
        requests.head(href).raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ValueError(
            f"Asset not accessible: {e.response.status_code} {e.response.reason}"
        )


@functools.lru_cache()
def collection_exists(collection_id: str) -> bool:
    """
    Ensure collection exists in STAC
    """
    from src.main import settings

    url = "/".join(
        f'{str(url).strip("/")}' for url in [settings.stac_url, "collections", collection_id]
    )

    if (response := requests.get(url)).ok:
        return True

    raise ValueError(
        f"Invalid collection '{collection_id}', received "
        f"{response.status_code} response code from STAC API"
    )
