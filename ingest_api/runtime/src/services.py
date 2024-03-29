import decimal
from typing import TYPE_CHECKING, List, Optional

import src.schemas as schemas
from boto3.dynamodb import conditions
from boto3.dynamodb.types import DYNAMODB_CONTEXT
from pydantic import parse_obj_as

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table


DYNAMODB_CONTEXT.traps[decimal.Rounded] = 0


class Database:
    def __init__(self, table: "Table"):
        self.table = table

    def write(self, ingestion: schemas.Ingestion):
        self.table.put_item(Item=ingestion.dynamodb_dict())

    def fetch_one(self, username: str, ingestion_id: str):
        response = self.table.get_item(
            Key={"created_by": username, "id": ingestion_id},
        )
        try:
            return schemas.Ingestion.parse_obj(response["Item"])
        except KeyError:
            raise NotInDb("Record not found")

    def fetch_many(
        self, status: str, next: Optional[dict] = None, limit: Optional[int] = None
    ) -> schemas.ListIngestionResponse:
        response = self.table.query(
            IndexName="status",
            KeyConditionExpression=conditions.Key("status").eq(status),
            **{"Limit": limit} if limit else {},
            **{"ExclusiveStartKey": next} if next else {},
        )
        return {
            "items": parse_obj_as(List[schemas.Ingestion], response["Items"]),
            "next": response.get("LastEvaluatedKey"),
        }


class NotInDb(Exception):
    ...
