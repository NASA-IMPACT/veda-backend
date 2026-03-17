"""
Unit tests for VedaCrudClient._search_base in core.py
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core import VedaCrudClient, ExtendedSearchRequest

from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.types.search import PgstacSearch


def make_client():
    """Create a VedaCrudClient instance without calling __init__."""
    return VedaCrudClient.__new__(VedaCrudClient)


class TestSearchBase:
    """
    Test cases VedaCrudClient.

    This class contains unit tests to ensure that the Veda STAC API Client class functions correctly. Specifically _search_base
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize mocks"""
        default_tiler = "https://fake-titiler.example.com"
        override_tiler = "https://fake-titiler-override.example.com"
        mock_data = {"collections": ["noaa-emergency-response"], "limit": 5, "tiler_url": override_tiler}
        mock_dict = MagicMock(spec=ExtendedSearchRequest)
        mock_dict.tiler_url = mock_data["tiler_url"]

        self.client = make_client()
        self.search_request = mock_dict
        self.request = MagicMock()
        self.override_tiler = override_tiler
        self.default_tiler = default_tiler


    async def test_tiler_url_overrides(
        self
    ):
        """Generate expected links and rendered_preview asset for each item with override tiler_url."""
        client = self.client
        search_request = self.search_request
        request = self.request

        # @NOTE-SANDRA: To be replaced once 572 merges
        valid_stac_collection_renders_with_dashboard = {
            "id": "test-collection",
            "type": "FeatureCollection",
            "features": [{
                "id": "test-item",
                "type": "Feature",
                "collection": "test-collection",
                "links": [],
                "assets": {},
                "geometry": None,
                "bbox": None,
                "properties": {"datetime": "2021-01-01T00:00:00Z"},
                "stac_version": "1.0.0",
                "stac_extensions": [],
            }],
            "links": [],
            "stac_version": "1.0.0",
            "renders": {
              "dashboard": {"nodata": -9999, "assets": ["burnRatio"]}
            },
        }

        with patch.object(
            CoreCrudClient, "_search_base", new_callable=AsyncMock
        ) as mock_super_search, patch.object(
            CoreCrudClient, "get_collection", new_callable=AsyncMock
        ) as mock_get_collection, patch(
            "src.links.tiles_settings.titiler_endpoint",
            new=self.default_tiler,
        ):
            mock_super_search.return_value = (
                valid_stac_collection_renders_with_dashboard
            )
            mock_get_collection.return_value = (
                valid_stac_collection_renders_with_dashboard
            )

            returned = await client._search_base(search_request, request=request)

        links = returned["features"][0]["links"]
        assets = returned["features"][0]["assets"]

        assert self.override_tiler in links[0]['href']
        assert self.override_tiler in assets['rendered_preview']['href']
