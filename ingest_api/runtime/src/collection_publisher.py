import logging
import os
from typing import Any, Dict, Optional

from pypgstac.db import PgstacDB
from src.config import settings
from src.schemas import DashboardCollection
from src.utils import IngestionType, get_db_credentials, load_into_pgstac
from src.vedaloader import VEDALoader
from stac_pydantic import Item

logger = logging.getLogger(__name__)


class CollectionPublisher:
    def ingest(self, collection: DashboardCollection):
        """
        Takes a collection model,
        does necessary preprocessing,
        and loads into the PgSTAC collection table
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        collection = [collection.to_dict(exclude_unset=True)]
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            load_into_pgstac(
                db=db, ingestions=collection, table=IngestionType.collections
            )

    def delete(self, collection_id: str):
        """
        Deletes the collection from the database
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            loader = VEDALoader(db=db)
            loader.delete_collection(collection_id)

    def get_collection_tenant(self, collection_id: str) -> Optional[str]:
        """Return tenant field from collection JSON in PgSTAC, or None if not found"""
        tenant_field = settings.tenant_filter_field
        logger.debug(
            "Resolving tenant for collection %s using tenant_field=%s",
            collection_id,
            tenant_field,
        )
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        try:
            with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
                collection_content = db.query_one(
                    "SELECT content FROM collections WHERE id=%s",
                    (collection_id,),
                )
        except Exception:
            logger.warning(
                "Could not load collection %s for tenant lookup (tenant_field=%s)",
                collection_id,
                tenant_field,
            )
            return None
        logger.debug(
            "collection_content shape for %s is collection_content_type=%s",
            collection_id,
            type(collection_content).__name__,
        )
        content_dict: Optional[Dict[str, Any]] = None
        if isinstance(collection_content, tuple) and collection_content:
            content_dict = collection_content[0]
        elif isinstance(collection_content, dict):
            content_dict = collection_content
        logger.debug(
            "collection_content normalized for %s: normalized_is_dict=%s tenant_field_present=%s",
            collection_id,
            isinstance(content_dict, dict),
            isinstance(content_dict, dict) and tenant_field in content_dict,
        )
        if isinstance(content_dict, dict):
            tenant_value = content_dict.get(tenant_field)
            if tenant_value:
                logger.info(
                    "Resolved tenant for collection %s: tenant_field=%s tenant=%s source=content(canonical)",
                    collection_id,
                    tenant_field,
                    tenant_value,
                )
                return str(tenant_value)
            logger.debug(
                "Collection %s has no value for tenant_field=%s in content",
                collection_id,
                tenant_field,
            )
            return None
        logger.debug(
            "Collection %s content payload is not a dict during tenant lookup",
            collection_id,
        )
        return None


class ItemPublisher:
    def ingest(self, item: Item):
        """
        Takes an item model,
        does necessary preprocessing,
        and loads into the PgSTAC item table
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        item = [item.to_dict()]
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            load_into_pgstac(db=db, ingestions=item, table=IngestionType.items)
