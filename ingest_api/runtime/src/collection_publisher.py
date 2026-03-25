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
                loader = VEDALoader(db=db)
                base_item: Dict[str, Any]
                base_item, _, _ = loader.collection_json(collection_id)
        except Exception:
            logger.warning(
                "Could not load collection %s for tenant lookup (tenant_field=%s)",
                collection_id,
                tenant_field,
            )
            return None
        if not isinstance(base_item, dict):
            logger.debug(
                "Collection %s payload is not a dict during tenant lookup",
                collection_id,
            )
            return None
        val = base_item.get(tenant_field)
        if not val:
            logger.debug(
                "Collection %s has no value for tenant_field=%s",
                collection_id,
                tenant_field,
            )
            return None
        logger.info(
            "Resolved tenant for collection %s: tenant_field=%s tenant=%s",
            collection_id,
            tenant_field,
            val,
        )
        return str(val) if val else None


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
