"""
Unit tests for VedaCrudClient._search_base in core.py
@NOTE-SANDRA: Ask if we should move into .github/workflows/tests/ ?
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.types.search import PgstacSearch

from src.core import VedaCrudClient


def make_client():
    """Create a VedaCrudClient instance without calling __init__."""
    return VedaCrudClient.__new__(VedaCrudClient)


def make_item(collection_id="test-collection"):
    return {
        "id": "test-item",
        "type": "Feature",
        "collection": collection_id,
        "links": [],
        "assets": {},
        "geometry": None,
        "bbox": None,
        "properties": {"datetime": "2021-01-01T00:00:00Z"},
        "stac_version": "1.0.0",
        "stac_extensions": [],
    }


def make_item_collection(features=None):
    return {"type": "FeatureCollection", "features": features or [], "links": []}


class TestSearchBase:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = make_client()
        self.search_request = MagicMock(spec=PgstacSearch)
        self.request = MagicMock()

    async def test_empty_features_returns_result_unchanged(self):
        """When result has no features, return the result as-is without calling get_collection."""
        client = self.client
        search_request = self.search_request
        request = self.request

        empty_result = make_item_collection([])

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection:
            mock_super_search.return_value = empty_result

            result = await client._search_base(search_request, request=request)

            assert result == empty_result
            mock_get_collection.assert_not_called()

    async def test_features_without_dashboard_renders_returns_result_unchanged(self):
        """When collection has no 'dashboard' key in renders, return result unchanged."""
        client = self.client
        search_request = self.search_request
        request = self.request

        item = make_item()
        result = make_item_collection([item])
        collection = {"id": "test-collection", "renders": {"other": {}}}

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection:
            mock_super_search.return_value = result
            mock_get_collection.return_value = collection

            returned = await client._search_base(search_request, request=request)

            assert returned == result

    async def test_features_with_no_renders_returns_result_unchanged(self):
        """When collection has no 'renders' key at all, return result unchanged."""
        client = self.client
        search_request = self.search_request
        request = self.request

        item = make_item()
        result = make_item_collection([item])
        collection = {"id": "test-collection"}

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection:
            mock_super_search.return_value = result
            mock_get_collection.return_value = collection

            returned = await client._search_base(search_request, request=request)

            assert returned == result

    async def test_features_with_dashboard_renders_injects_links(self):
        """When collection has 'dashboard' renders, expected links and rendered_preview asset are injected into each item."""
        client = self.client
        search_request = self.search_request
        request = self.request

        item = make_item()
        result = make_item_collection([item])
        render_params = {"nodata": -9999, "assets": ["burnRatio"]}
        collection = {
            "id": "test-collection",
            "renders": {"dashboard": render_params},
        }

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection, patch(
            "src.links.tiles_settings.titiler_endpoint",
            new="https://fake-titiler.example.com",
        ):
            mock_super_search.return_value = result
            mock_get_collection.return_value = collection

            returned = await client._search_base(search_request, request=request)
        assert "features" in returned
        assert len(returned["features"]) == 1

        links = returned["features"][0]["links"]
        assets = returned["features"][0]["assets"]
        expected_key = "title"
        expected_value = "Map of Item"
        assert any(d.get(expected_key) == expected_value for d in links)
        assert "rendered_preview" in assets