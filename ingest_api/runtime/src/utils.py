from enum import Enum
from typing import Sequence, Union

import boto3
import pydantic
from pypgstac.db import PgstacDB
from pypgstac.load import Methods
from src.schemas import AccessibleItem, DashboardCollection
from src.vedaloader import VEDALoader


class IngestionType(str, Enum):
    collections = "collections"
    items = "items"


class DbCreds(pydantic.BaseModel):
    username: str
    password: str
    host: str
    port: int
    dbname: str
    engine: str

    @property
    def dsn_string(self) -> str:
        return f"{self.engine}://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}"  # noqa


def get_db_credentials(secret_arn: str) -> DbCreds:
    """
    Load pgSTAC database credentials from AWS Secrets Manager.
    """
    print("Fetching DB credentials...")
    session = boto3.session.Session(region_name=secret_arn.split(":")[3])
    client = session.client(service_name="secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return DbCreds.parse_raw(response["SecretString"])


def load_items(items: Sequence[AccessibleItem], loader):
    """
    Loads items into the PgSTAC database and
    updates the summaries and extent for the collections involved
    """
    loading_result = loader.load_items(
        file=items,
        # use insert_ignore to avoid overwritting existing items or upsert to replace
        insert_mode=Methods.upsert,
    )

    # Trigger update on summaries and extents
    collections = set([item["collection"] for item in items])
    for collection in collections:
        loader.update_collection_summaries(collection)

    return loading_result


def load_collection(collection: Sequence[DashboardCollection], loader):
    """
    Loads the collection to the PgSTAC database
    """
    return loader.load_collections(
        file=collection,
        # use insert_ignore to avoid overwritting existing items or upsert to replace
        insert_mode=Methods.upsert,
    )


def load_into_pgstac(
    db: "PgstacDB",
    ingestions: Union[Sequence[AccessibleItem], Sequence[DashboardCollection]],
    table: IngestionType,
):
    """
    Bulk insert STAC records into pgSTAC.
    The ingestion can be items or collection, determined by the `table` arg.
    """
    loader = VEDALoader(db=db)
    loading_function = load_items
    if table == IngestionType.collections:
        loading_function = load_collection  # type: ignore
    return loading_function(ingestions, loader)
