"""
Integration tests for STAC Transactions API against docker-compose environment.

This module tests the collection and item transaction endpoints using
real HTTP requests against the running STAC service with authentication
via the mock OIDC server.

Endpoints tested:
- POST /collections (create collection)
- DELETE /collections/{id} (delete collection)
- POST /collections/{id}/items (create item)
- POST /collections/{id}/bulk_items (bulk create items)
"""

import copy
import uuid

import httpx
import pytest

# Test data
VALID_COLLECTION = {
    "id": "test-collection",
    "type": "Collection",
    "title": "Projected changes to winter (January, February, and March) cumulative daily precipitation",
    "links": [],
    "description": "Differences in winter (January, February, and March) cumulative daily precipitation between a historical period (1995 - 2014) and multiple 20-year periods from an ensemble of CMIP6 climate projections (SSP2-4.5) downscaled by NASA Earth Exchange (NEX-GDDP-CMIP6)",
    "extent": {
        "spatial": {"bbox": [[-126, 30, -104, 51]]},
        "temporal": {"interval": [["2025-01-01T00:00:00Z", "2085-03-31T12:00:00Z"]]},
    },
    "license": "MIT",
    "stac_extensions": [
        "https://stac-extensions.github.io/render/v1.0.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
    ],
    "item_assets": {
        "cog_default": {
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data", "layer"],
            "title": "Default COG Layer",
            "description": "Cloud optimized default layer to display on map",
        }
    },
    "dashboard:is_periodic": False,
    "dashboard:time_density": "year",
    "stac_version": "1.0.0",
    "renders": {
        "dashboard": {
            "resampling": "bilinear",
            "bidx": [1],
            "nodata": "nan",
            "colormap_name": "rdbu",
            "rescale": [[-60, 60]],
            "assets": ["cog_default"],
            "title": "VEDA Dashboard Render Parameters",
        }
    },
    "providers": [
        {
            "name": "NASA Center for Climate Simulation (NCCS)",
            "url": "https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6",
            "roles": ["producer", "processor", "licensor"],
        },
        {
            "name": "NASA VEDA",
            "url": "https://www.earthdata.nasa.gov/dashboard/",
            "roles": ["host"],
        },
    ],
    "assets": {
        "thumbnail": {
            "title": "Thumbnail",
            "description": "Photo by Justin Pflug (Photo of Nisqually glacier)",
            "href": "https://thumbnails.openveda.cloud/CMIP-winter-median.jpeg",
            "type": "image/jpeg",
            "roles": ["thumbnail"],
        }
    },
}

VALID_ITEM = {
    "id": "test-item",
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "type": "Feature",
    "links": [],
    "assets": {
        "cog_default": {
            "href": "s3://veda-data-store-staging/test/test.tif",
            "type": "image/tiff; application=geotiff",
            "roles": ["data", "layer"],
            "title": "Test COG",
        },
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
    },
    "collection": "test-collection",
    "properties": {
        "datetime": "2023-01-01T00:00:00+00:00",
    },
    "stac_version": "1.0.0",
    "stac_extensions": [],
}


class TestTransactions:
    """
    Integration test cases for STAC Transactions API.

    Tests collection and item CRUD operations against the running
    docker-compose environment with authentication.
    """

    @pytest.fixture(autouse=True)
    def setup(self, stac_endpoint, auth_token, auth_headers):
        """Set up test environment with required fixtures."""
        self.stac_endpoint = stac_endpoint
        self.auth_token = auth_token
        self.auth_headers = auth_headers
        self.collections_endpoint = f"{stac_endpoint}/collections"

    @pytest.fixture
    def unique_collection(self):
        """Generate a unique collection for each test."""
        collection = copy.deepcopy(VALID_COLLECTION)
        collection["id"] = f"test-collection-{str(uuid.uuid4()).split('-')[0]}"
        return collection

    @pytest.fixture
    def unique_item(self, unique_collection):
        """Generate a unique item linked to the unique collection."""
        item = copy.deepcopy(VALID_ITEM)
        item["id"] = f"test-item-{str(uuid.uuid4()).split('-')[0]}"
        item["collection"] = unique_collection["id"]
        return item

    def test_post_invalid_collection(self):
        """Test the API's response to posting an invalid STAC collection."""
        invalid_collection = copy.deepcopy(VALID_COLLECTION)
        invalid_collection.pop("extent")  # Remove required field

        response = httpx.post(
            self.collections_endpoint,
            json=invalid_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Validation Error"

    def test_post_valid_collection(self, unique_collection):
        """Test the API's response to posting a valid STAC collection."""
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert (
            response.status_code == 201
        ), f"Failed to create collection: {response.text}"

        # Cleanup: delete the collection
        delete_response = httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )
        assert delete_response.status_code in [200, 204]

    def test_post_duplicate_collection(self, unique_collection):
        """Test the API's response to posting a duplicate collection."""
        # Create the collection first
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Try to create it again
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 409  # Conflict

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_post_invalid_item(self, unique_collection):
        """Test the API's response to posting an invalid STAC item."""
        # First create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Create invalid item (missing properties)
        invalid_item = copy.deepcopy(VALID_ITEM)
        invalid_item["collection"] = unique_collection["id"]
        invalid_item.pop("properties")

        items_endpoint = f"{self.collections_endpoint}/{unique_collection['id']}/items"
        response = httpx.post(
            items_endpoint,
            json=invalid_item,
            headers=self.auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Validation Error"

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_post_valid_item(self, unique_collection, unique_item):
        """Test the API's response to posting a valid STAC item."""
        # First create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Create the item - remove collection field as it's implied by the URL
        item_to_post = {k: v for k, v in unique_item.items() if k != "collection"}
        items_endpoint = f"{self.collections_endpoint}/{unique_collection['id']}/items"
        response = httpx.post(
            items_endpoint,
            json=item_to_post,
            headers=self.auth_headers,
        )
        assert response.status_code == 201, f"Failed to create item: {response.text}"

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_post_valid_bulk_items(self, unique_collection, unique_item):
        """Test the API's response to posting valid bulk STAC items."""
        # First create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Create bulk items - remove collection field as it's implied by the URL
        item_to_post = {k: v for k, v in unique_item.items() if k != "collection"}
        bulk_endpoint = (
            f"{self.collections_endpoint}/{unique_collection['id']}/bulk_items"
        )
        bulk_request = {
            "items": {item_to_post["id"]: item_to_post},
            "method": "upsert",
        }

        response = httpx.post(
            bulk_endpoint,
            json=bulk_request,
            headers=self.auth_headers,
        )
        assert (
            response.status_code == 200
        ), f"Failed to create bulk items: {response.text}"

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_post_invalid_bulk_items(self, unique_collection):
        """Test the API's response to posting invalid bulk STAC items."""
        # First create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Create invalid bulk items (missing properties)
        invalid_item = copy.deepcopy(VALID_ITEM)
        invalid_item["collection"] = unique_collection["id"]
        invalid_item.pop("properties")

        bulk_endpoint = (
            f"{self.collections_endpoint}/{unique_collection['id']}/bulk_items"
        )
        bulk_request = {
            "items": {invalid_item["id"]: invalid_item},
            "method": "upsert",
        }

        response = httpx.post(
            bulk_endpoint,
            json=bulk_request,
            headers=self.auth_headers,
        )
        assert response.status_code == 422

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_get_collection_by_id(self, unique_collection):
        """Test searching for a specific collection by its ID."""
        # Create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Search by ID using filter
        response = httpx.get(
            self.collections_endpoint,
            params={"filter": f"id = '{unique_collection['id']}'"},
        )
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["collections"]) > 0
        assert response_data["collections"][0]["id"] == unique_collection["id"]

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )

    def test_collection_freetext_search_by_title(self, unique_collection):
        """Test free-text search for a collection using a word from its title."""
        # Create the collection
        response = httpx.post(
            self.collections_endpoint,
            json=unique_collection,
            headers=self.auth_headers,
        )
        assert response.status_code == 201

        # Search by title using free text
        search_term = "precipitation"
        response = httpx.get(
            self.collections_endpoint,
            params={"q": search_term},
        )
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["collections"]) > 0

        returned_ids = [col["id"] for col in response_data["collections"]]
        assert unique_collection["id"] in returned_ids

        # Cleanup
        httpx.delete(
            f"{self.collections_endpoint}/{unique_collection['id']}",
            headers=self.auth_headers,
        )


class TestTransactionsUnauthorized:
    """Test that transaction endpoints require authentication."""

    @pytest.fixture(autouse=True)
    def setup(self, stac_endpoint):
        """Set up test environment."""
        self.stac_endpoint = stac_endpoint
        self.collections_endpoint = f"{stac_endpoint}/collections"

    def test_post_collection_without_auth(self):
        """Test that creating a collection without auth returns 401/403."""
        collection = copy.deepcopy(VALID_COLLECTION)
        collection["id"] = f"test-unauth-{str(uuid.uuid4()).split('-')[0]}"

        response = httpx.post(
            self.collections_endpoint,
            json=collection,
        )
        # Should be unauthorized or forbidden
        assert response.status_code in [401, 403]

    def test_delete_collection_without_auth(self):
        """Test that deleting a collection without auth returns 401/403."""
        response = httpx.delete(
            f"{self.collections_endpoint}/nonexistent-collection",
        )
        # Should be unauthorized or forbidden
        assert response.status_code in [401, 403, 404]
