"""
Unit tests for VedaCrudClient._search_base in core.py
@NOTE-SANDRA: Ask if we should move into .github/workflows/tests/ ?
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core import VedaCrudClient

from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.types.search import PgstacSearch


def make_client():
    """Create a VedaCrudClient instance without calling __init__."""
    return VedaCrudClient.__new__(VedaCrudClient)


def make_item(collection_id="test-collection"):
    """Create a test item"""
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
    """Create a test item collection"""
    return {"type": "FeatureCollection", "features": features or [], "links": []}


class TestSearchBase:
    """
    Test cases VedaCrudClient.

    This class contains unit tests to ensure that the Veda STAC API Client class functions correctly. Specifically _search_base
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize mocks"""
        self.client = make_client()
        self.search_request = MagicMock(spec=PgstacSearch)
        self.request = MagicMock()

    async def test_empty_features_returns_result_unchanged(self, valid_stac_features_collection_empty):
        """When result has no features, return the result as-is without calling get_collection."""
        client = self.client
        search_request = self.search_request
        request = self.request

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection:
            mock_super_search.return_value = valid_stac_features_collection_empty

            result = await client._search_base(search_request, request=request)

            assert result == valid_stac_features_collection_empty
            mock_get_collection.assert_not_called()

    async def test_features_without_dashboard_renders_returns_result_unchanged(self, valid_stac_collection_multi_cog_asset_renders):
        """When collection has no 'dashboard' key in renders, return result unchanged."""
        client = self.client
        search_request = self.search_request
        request = self.request

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection:
            mock_super_search.return_value = valid_stac_collection_multi_cog_asset_renders
            mock_get_collection.return_value = valid_stac_collection_multi_cog_asset_renders

            returned = await client._search_base(search_request, request=request)

            assert returned == valid_stac_collection_multi_cog_asset_renders

    # Old logic -> make sure works as expected
    async def test_features_with_dashboard_renders_injects_links(self, valid_stac_collection_multi_cog_asset_renders_with_dashboard):
        """When collection has 'dashboard' renders, expected links and rendered_preview asset are injected into each item."""
        client = self.client
        search_request = self.search_request
        request = self.request

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection, patch(
            "src.links.tiles_settings.titiler_endpoint",
            new="https://fake-titiler.example.com",
        ):
            mock_super_search.return_value = valid_stac_collection_multi_cog_asset_renders_with_dashboard
            mock_get_collection.return_value = valid_stac_collection_multi_cog_asset_renders_with_dashboard

            returned = await client._search_base(search_request, request=request)
        assert "features" in returned
        assert len(returned["features"]) == 1

        links = returned["features"][0]["links"]
        assets = returned["features"][0]["assets"]
        expected_key = "title"
        expected_value = "Map of Item for dashboard"
        assert any(d.get(expected_key) == expected_value for d in links)
        assert "rendered_preview_dashboard" in assets

    async def test_features_with_renders_injects_links(self, valid_stac_collection_multi_cog_asset_renders_with_dashboard):
        """Generate expected links and rendered_preview asset for each item."""
        client = self.client
        search_request = self.search_request
        request = self.request

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection, patch(
            "src.links.tiles_settings.titiler_endpoint",
            new="https://fake-titiler.example.com",
        ):
            mock_super_search.return_value = valid_stac_collection_multi_cog_asset_renders_with_dashboard
            mock_get_collection.return_value = valid_stac_collection_multi_cog_asset_renders_with_dashboard

            returned = await client._search_base(search_request, request=request)
        assert "features" in returned
        assert len(returned["features"]) == 1

        links = returned["features"][0]["links"]
        titles = [link["title"] for link in links]
        expected_map_link_title_values = [
            "Map of Item for colorIR",
            "Map of Item for burnRatio",
            "Map of Item for dashboard",
        ]
        # Check that all expected Map links are generated for all assets in render config
        assert titles == expected_map_link_title_values

        assets = returned["features"][0]["assets"]
        assets_keys = list(assets.keys())
        expected_render_assets = [
            "rendered_preview_colorIR",
            "rendered_preview_burnRatio",
            "rendered_preview_dashboard",
        ]
        # Check that all expected render previews are generated for all assets in render config
        assert assets_keys == expected_render_assets
