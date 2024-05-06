import os
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Iterator, List, Optional, Sequence

from boto3.dynamodb.types import TypeDeserializer
from pypgstac.db import PgstacDB
from src.dependencies import get_table
from src.schemas import Ingestion, Status
from src.utils import IngestionType, get_db_credentials, load_into_pgstac

from fastapi.encoders import jsonable_encoder

if TYPE_CHECKING:
    from aws_lambda_typing import context as context_
    from aws_lambda_typing import events
    from aws_lambda_typing.events.dynamodb_stream import DynamodbRecord


def get_queued_ingestions(records: List["DynamodbRecord"]) -> Iterator[Ingestion]:
    deserializer = TypeDeserializer()
    for record in records:
        # Parse Record
        parsed = {
            k: deserializer.deserialize(v)
            for k, v in record["dynamodb"]["NewImage"].items()
        }
        ingestion = Ingestion.parse_obj(parsed)
        if ingestion.status == Status.queued:
            yield ingestion


def update_dynamodb(
    ingestions: Sequence[Ingestion],
    status: Status,
    message: Optional[str] = None,
):
    """
    Bulk update DynamoDB with ingestion results.
    """
    # Update records in DynamoDB
    print(f"Updating ingested items status in DynamoDB, marking as {status}...")
    table = get_table()
    with table.batch_writer(overwrite_by_pkeys=["created_by", "id"]) as batch:
        for ingestion in ingestions:
            batch.put_item(
                Item=ingestion.copy(
                    update={
                        "status": status,
                        "message": message,
                        "updated_at": datetime.now(),
                    }
                ).dynamodb_dict()
            )


def handler(event: "events.DynamoDBStreamEvent", context: "context_.Context"):
    # Parse input
    ingestions = list(get_queued_ingestions(event["Records"]))
    if not ingestions:
        print("No queued ingestions to process")
        return

    # serialize to JSON-friendly dicts (won't be necessary in Pydantic v2, https://github.com/pydantic/pydantic/issues/1409#issuecomment-1423995424)
    items = jsonable_encoder(i.item for i in ingestions)

    creds = get_db_credentials(os.environ["DB_SECRET_ARN"])

    # Insert into PgSTAC DB
    outcome = Status.succeeded
    message = None
    try:
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            load_into_pgstac(
                db=db,
                ingestions=items,
                table=IngestionType.items,
            )
    except Exception as e:
        traceback.print_exc()
        print(f"Encountered failure loading items into pgSTAC: {e}")
        outcome = Status.failed
        message = str(e)

    # Update DynamoDB with outcome
    update_dynamodb(
        ingestions=ingestions,
        status=outcome,
        message=message,
    )

    print("Completed batch...")
