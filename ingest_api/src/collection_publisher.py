import os

from pypgstac.db import PgstacDB
from src.schemas import DashboardCollection
from src.utils import (
    IngestionType,
    convert_decimals_to_float,
    get_db_credentials,
    load_into_pgstac,
)
from src.vedaloader import VEDALoader


class CollectionPublisher:
    common_fields = [
        "title",
        "description",
        "license",
        "links",
        "time_density",
        "is_periodic",
    ]
    common = {
        "links": [],
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "type": "Collection",
        "stac_version": "1.0.0",
    }

    def ingest(self, collection: DashboardCollection):
        """
        Takes a collection model,
        does necessary preprocessing,
        and loads into the PgSTAC collection table
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        collection = [convert_decimals_to_float(collection.dict(by_alias=True))]
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
