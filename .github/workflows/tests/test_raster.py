"""test veda-backend.raster."""

import httpx
import pytest


class TestList:
    """
    Test cases for Raster API.

    This class contains integration tests to ensure that the Raster API functions correctly

    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        collections_endpoint,
        docs_endpoint,
        index_endpoint,
        seeded_collection,
        seeded_id,
        raster_endpoint,
        raster_health_endpoint,
        seeded_tilematrix,
        searches,
    ):
        """
        Set up the test environment with the required fixtures.
        """
        self.collections_endpoint = collections_endpoint
        self.docs_endpoint = docs_endpoint
        self.index_endpoint = index_endpoint
        self.seeded_collection = seeded_collection
        self.seeded_id = seeded_id
        self.raster_endpoint = raster_endpoint
        self.raster_health_endpoint = raster_health_endpoint
        self.seeded_tilematrix = seeded_tilematrix
        self.searches = searches

    def test_raster_api_health(self):
        """test api."""
        # health
        resp = httpx.get(
            f"{self.raster_endpoint}/healthz", headers={"Accept-Encoding": "br, gzip"}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert resp.headers["content-encoding"] in ["br", "gzip"]

    def test_mosaic_api(self):
        """test mosaic."""
        query = {"collections": [self.seeded_collection], "filter-lang": "cql-json"}
        resp = httpx.post(f"{self.raster_endpoint}/searches/register", json=query)
        assert resp.headers["content-type"] == "application/json"
        assert resp.status_code == 200
        assert resp.json()["searchid"]
        assert resp.json()["links"]

        searchid = resp.json()["searchid"]
        assert resp.status_code == 200

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/{searchid}/-85.6358,36.1624/assets"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
        assert resp.json()[0]["id"] == self.seeded_id

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/{searchid}/tiles/15/8589/12849/assets"
        )

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
        assert resp.json()[0]["id"] == self.seeded_id

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/{searchid}/tiles/{self.seeded_tilematrix['z']}/{self.seeded_tilematrix['x']}/{self.seeded_tilematrix['y']}",
            params={"assets": "cog"},
            headers={"Accept-Encoding": "br, gzip"},
            timeout=10.0,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert "content-encoding" not in resp.headers

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/{searchid}/tiles/{self.seeded_tilematrix['z']}/{self.seeded_tilematrix['x']}/{self.seeded_tilematrix['y']}/assets"
        )
        assert resp.status_code == 200

    def test_mosaic_search(self):
        """test mosaic."""
        # register some fake mosaic
        for search in self.searches:
            resp = httpx.post(f"{self.raster_endpoint}/searches/register", json=search)
            assert resp.status_code == 200
            assert resp.json()["searchid"]

        resp = httpx.get(f"{self.raster_endpoint}/searches/list")
        assert resp.headers["content-type"] == "application/json"
        assert resp.status_code == 200
        assert (
            resp.json()["context"]["matched"] > 10
        )  # there should be at least 12 mosaic registered
        assert resp.json()["context"]["returned"] == 10  # default limit is 10

        # Make sure all mosaics returned have
        for search in resp.json()["searches"]:
            assert search["search"]["metadata"]["type"] == "mosaic"

        links = resp.json()["links"]
        assert len(links) == 2
        assert links[0]["rel"] == "self"
        assert links[1]["rel"] == "next"
        assert (
            links[1]["href"] == f"{self.raster_endpoint}/searches/list?limit=10&offset=10"
        )

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"limit": 1, "offset": 1}
        )
        assert resp.status_code == 200
        assert resp.json()["context"]["matched"] > 10
        assert resp.json()["context"]["limit"] == 1
        assert resp.json()["context"]["returned"] == 1

        links = resp.json()["links"]
        assert len(links) == 3
        assert links[0]["rel"] == "self"

        assert (
            links[0]["href"] == f"{self.raster_endpoint}/searches/list?limit=1&offset=1"
        )
        assert links[1]["rel"] == "next"
        assert (
            links[1]["href"] == f"{self.raster_endpoint}/searches/list?limit=1&offset=2"
        )
        assert links[2]["rel"] == "prev"
        assert (
            links[2]["href"] == f"{self.raster_endpoint}/searches/list?limit=1&offset=0"
        )

        # Filter on mosaic metadata
        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"owner": "vincent"}
        )
        assert resp.status_code == 200
        assert resp.json()["context"]["matched"] == 7
        assert resp.json()["context"]["limit"] == 10
        assert resp.json()["context"]["returned"] == 7

        # sortBy
        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"sortby": "lastused"}
        )
        assert resp.status_code == 200

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"sortby": "usecount"}
        )
        assert resp.status_code == 200

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"sortby": "-owner"}
        )
        assert resp.status_code == 200
        assert (
            "owner" not in resp.json()["searches"][0]["search"]["metadata"]
        )  # some mosaic don't have owners

        resp = httpx.get(
            f"{self.raster_endpoint}/searches/list", params={"sortby": "owner"}
        )
        assert resp.status_code == 200
        assert "owner" in resp.json()["searches"][0]["search"]["metadata"]
