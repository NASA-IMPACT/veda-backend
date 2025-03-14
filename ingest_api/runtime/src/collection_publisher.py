import os

from pypgstac.db import PgstacDB
from src.schemas import DashboardCollection
from src.utils import IngestionType, get_db_credentials, load_into_pgstac
from src.vedaloader import VEDALoader
from stac_pydantic import Item


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
