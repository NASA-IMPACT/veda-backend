import base64
import json
from datetime import timedelta

# from math import isclose
from typing import TYPE_CHECKING, List

import pytest

from fastapi.encoders import jsonable_encoder


if TYPE_CHECKING:
    from src import schemas, services

    from fastapi.testclient import TestClient

ingestion_endpoint = "/ingestions"


class TestList:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        api_client: "TestClient",
        mock_table: "services.Table",
        example_ingestion: "schemas.Ingestion",
    ):
        self.api_client = api_client
        self.mock_table = mock_table
        self.example_ingestion = example_ingestion

    def populate_table(self, count=100) -> List["schemas.Ingestion"]:
        example_ingestions = []
        for i in range(count):
            ingestion = self.example_ingestion.copy()
            ingestion.id = str(i)
            ingestion.created_at = ingestion.created_at + timedelta(hours=i)
            self.mock_table.put_item(Item=ingestion.dynamodb_dict())
            example_ingestions.append(ingestion)
        return example_ingestions

    def test_simple_lookup(self):
        self.mock_table.put_item(Item=self.example_ingestion.dynamodb_dict())
        ingestion = jsonable_encoder(self.example_ingestion)
        response = self.api_client.get(ingestion_endpoint)
        assert response.status_code == 200
        assert response.json() == {
            "items": [ingestion],
            "next": None,
        }

    def test_next_response(self):
        example_ingestions = self.populate_table(100)

        limit = 25
        expected_next = json.loads(
            example_ingestions[limit - 1].json(
                include={"created_by", "id", "status", "created_at"}
            )
        )

        response = self.api_client.get(ingestion_endpoint, params={"limit": limit})
        assert response.status_code == 200
        assert json.loads(base64.b64decode(response.json()["next"])) == expected_next
        assert response.json()["items"] == jsonable_encoder(example_ingestions[:limit])

