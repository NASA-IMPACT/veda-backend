"""test veda-backend STAC."""
import httpx
import pytest


class TestList:
    """
    Test cases for STAC API.

    This class contains integration tests to ensure that the STAC API functions correctly

    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        collections_route,
        docs_route,
        index_route,
        search_route,
        seeded_collection,
        seeded_id,
        stac_endpoint,
        stac_health_endpoint,
    ):
        """
        Set up the test environment with the required fixtures.
        """
        self.collections_route = collections_route
        self.docs_route = docs_route
        self.index_route = index_route
        self.search_route = search_route
        self.seeded_collection = seeded_collection
        self.seeded_id = seeded_id
        self.stac_endpoint = stac_endpoint
        self.stac_health_endpoint = stac_health_endpoint

    def test_stac_health(self):
        """test stac health endpoint."""

        assert httpx.get(self.stac_health_endpoint).status_code == 200

    def test_stac_viewer(self):
        """test stac viewer."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.index_route}")
        assert resp.status_code == 200
        assert resp.headers.get("x-correlation-id") == "local"
        assert "<title>Simple STAC API Viewer</title>" in resp.text

    def test_stac_docs(self):
        """test stac docs."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.docs_route}")
        assert resp.status_code == 200
        assert "Swagger UI" in resp.text

    def test_stac_get_search(self):
        """test stac get search."""
        default_limit_param = "?limit=10"
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.search_route}{default_limit_param}"
        )
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) > 0
        collections = [c["collection"] for c in features]
        assert self.seeded_collection in collections

    def test_stac_post_search(self):
        """test stac post search."""
        request_body = {"collections": [self.seeded_collection]}
        resp = httpx.post(
            f"{self.stac_endpoint}/{self.search_route}", json=request_body
        )
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) > 0
        collections = [c["collection"] for c in features]
        assert self.seeded_collection in collections

    def test_stac_get_collections(self):
        """test stac get collections"""
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}")
        assert resp.status_code == 200
        collections = resp.json()["collections"]
        assert len(collections) > 0
        id = [c["id"] for c in collections]
        assert self.seeded_collection in id

    def test_stac_get_collections_by_id(self):
        """test stac get collection by id"""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}"
        )
        assert resp.status_code == 200
        collection = resp.json()
        assert collection["id"] == self.seeded_collection

    def test_stac_get_collection_items_by_id(self):
        """test stac get items in collection by collection id"""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items"
        )
        assert resp.status_code == 200
        collection = resp.json()
        assert collection["type"] == "FeatureCollection"

    def test_stac_api(self):
        """test stac."""

        # Collections
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}")
        assert resp.status_code == 200
        collections = resp.json()["collections"]
        assert len(collections) > 0
        ids = [c["id"] for c in collections]
        assert self.seeded_collection in ids

        # items
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items"
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) == 10

        # item
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}"
        )
        assert resp.status_code == 200
        item = resp.json()
        assert item["id"] == self.seeded_id

    def test_stac_to_raster(self):
        """test link to raster api."""
        # tilejson
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}/tilejson.json",
            params={"assets": "cog"},
        )
        assert resp.status_code == 307

        # viewer
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}/viewer",
            params={"assets": "cog"},
        )
        assert resp.status_code == 307
