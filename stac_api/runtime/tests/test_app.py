import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

index_endpoint = "/index.html"
docs_endpoint = "/docs"


class TestList:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        api_client: "TestClient",
        # pgstac_secret_arn = "app_secret"
    ):
        self.api_client = api_client
        # self.pgstac_secret_arn = pgstac_secret_arn

    @pytest.mark.anyio
    async def test_index(self):
        response = self.api_client.get(index_endpoint)
        assert response.status_code == 200
        print(response.headers)
        assert response.headers.get('x-correlation-id') == "local"
        assert "<title>Simple STAC API Viewer</title>" in response.text

    @pytest.mark.anyio
    async def test_docs(self):
        response = self.api_client.get(docs_endpoint)
        assert response.status_code == 200
        assert "Swagger UI" in response.text