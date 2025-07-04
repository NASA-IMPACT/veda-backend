import logging

import boto3
import src.services as services
from src.auth import get_username
from src.config import settings

from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)


def get_table():
    client = boto3.resource("dynamodb")
    return client.Table(settings.dynamodb_table)


def get_db(table=Depends(get_table)) -> services.Database:
    return services.Database(table=table)


def fetch_ingestion(
    ingestion_id: str,
    db: services.Database = Depends(get_db),
    username: str = Depends(get_username),
):
    try:
        return db.fetch_one(username=username, ingestion_id=ingestion_id)
    except services.NotInDb:
        raise HTTPException(
            status_code=404, detail="No ingestion found with provided ID"
        )
