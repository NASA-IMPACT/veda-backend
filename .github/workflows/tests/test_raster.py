"""test veda-backend.raster."""

import time

import httpx
import pytest

HTTP_TIMEOUT = 30.0


class TestList:
    """
    Test cases for Raster API.

    This class contains integration tests that ensure the Raster API functions correctly

    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        seeded_collection,
        seeded_id,
        raster_searches_endpoint,
        raster_health_endpoint,
        seeded_tilematrix,
        searches,
        seeded_tms_id,
    ):
        """
        Set up the test environment with the required fixtures.
        """
        self.seeded_collection = seeded_collection
        self.seeded_id = seeded_id
        self.raster_searches_endpoint = raster_searches_endpoint
        self.raster_health_endpoint = raster_health_endpoint
        self.seeded_tilematrix = seeded_tilematrix
        self.searches = searches
        self.seeded_tms_id = seeded_tms_id

    def _post_with_retry(self, url, json, attempts=5, delay=0.5):
        """Retry transient startup transport errors when local services are cold."""
        for attempt in range(1, attempts + 1):
            try:
                return httpx.post(url, json=json, timeout=HTTP_TIMEOUT)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == attempts:
                    raise
                time.sleep(delay)
        return None

    def _get_with_retry(self, url, attempts=5, delay=0.5, **kwargs):
        """Retry transient startup transport errors when local services are cold."""
        for attempt in range(1, attempts + 1):
            try:
                return httpx.get(url, timeout=HTTP_TIMEOUT, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == attempts:
                    raise
                time.sleep(delay)
        return None

    def test_raster_api_health(self):
        """test api."""
        # health
        resp = self._get_with_retry(
            self.raster_health_endpoint,
            headers={"Accept-Encoding": "br, gzip"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert resp.headers["content-encoding"] in ["br", "gzip"]

    def test_gaia_exposure_colormap(self):
        """gaia-exposure is packaged and served as an interval colormap."""
        resp = self._get_with_retry(
            f"{self.raster_health_endpoint.rsplit('/', 1)[0]}/colorMaps/gaia-exposure"
        )
        assert resp.status_code == 200
        assert resp.json() == [
            [[0, 25000], [63, 42, 107, 255]],
            [[25000, 50000], [62, 134, 158, 255]],
            [[50000, 75000], [115, 192, 195, 255]],
            [[75000, 100000], [195, 224, 156, 255]],
            [[100000, 150000], [247, 233, 156, 255]],
            [[150000, 300000], [243, 197, 86, 255]],
            [[300000, 450000], [231, 142, 65, 255]],
            [[450000, 10000000], [207, 73, 49, 255]],
        ]

    def test_mosaic_api(self):
        """test mosaic."""
        query = {"collections": [self.seeded_collection], "filter-lang": "cql-json"}
        resp = self._post_with_retry(
            f"{self.raster_searches_endpoint}/register", json=query
        )
        assert resp.headers["content-type"] == "application/json"
        assert resp.status_code == 200
        assert resp.json()["id"]
        assert resp.json()["links"]

        searchid = resp.json()["id"]
        assert resp.status_code == 200
        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/{searchid}/point/-85.6358,36.1624/assets",
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
        assert resp.json()[0]["id"] == self.seeded_id

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/{searchid}/tiles/{self.seeded_tms_id}/15/8589/12849/assets",
        )

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
        assert resp.json()[0]["id"] == self.seeded_id

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/{searchid}/tiles/{self.seeded_tms_id}/{self.seeded_tilematrix['z']}/{self.seeded_tilematrix['x']}/{self.seeded_tilematrix['y']}",
            params={"assets": "cog"},
            headers={"Accept-Encoding": "br, gzip"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert "content-encoding" not in resp.headers

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/{searchid}/tiles/{self.seeded_tms_id}/{self.seeded_tilematrix['z']}/{self.seeded_tilematrix['x']}/{self.seeded_tilematrix['y']}/assets",
        )
        assert resp.status_code == 200

    def test_mosaic_search(self):
        """test mosaic."""
        # register some fake mosaic
        for search in self.searches:
            resp = self._post_with_retry(
                f"{self.raster_searches_endpoint}/register", json=search
            )
            assert resp.status_code == 200
            assert resp.json()["id"]

        resp = self._get_with_retry(f"{self.raster_searches_endpoint}/list")
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
            links[1]["href"]
            == f"{self.raster_searches_endpoint}/list?limit=10&offset=10"
        )

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"limit": 1, "offset": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["context"]["matched"] > 10
        assert resp.json()["context"]["limit"] == 1
        assert resp.json()["context"]["returned"] == 1

        links = resp.json()["links"]
        assert len(links) == 3
        assert links[0]["rel"] == "self"

        assert (
            links[0]["href"] == f"{self.raster_searches_endpoint}/list?limit=1&offset=1"
        )
        assert links[1]["rel"] == "next"
        assert (
            links[1]["href"] == f"{self.raster_searches_endpoint}/list?limit=1&offset=2"
        )
        assert links[2]["rel"] == "prev"
        assert (
            links[2]["href"] == f"{self.raster_searches_endpoint}/list?limit=1&offset=0"
        )

        # Filter on mosaic metadata
        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"owner": "vincent"},
        )
        assert resp.status_code == 200
        assert resp.json()["context"]["matched"] == 7
        assert resp.json()["context"]["limit"] == 10
        assert resp.json()["context"]["returned"] == 7

        # sortBy
        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"sortby": "lastused"},
        )
        assert resp.status_code == 200

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"sortby": "usecount"},
        )
        assert resp.status_code == 200

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"sortby": "-owner"},
        )
        assert resp.status_code == 200
        assert (
            "owner" not in resp.json()["searches"][0]["search"]["metadata"]
        )  # some mosaic don't have owners

        resp = self._get_with_retry(
            f"{self.raster_searches_endpoint}/list",
            params={"sortby": "owner"},
        )
        assert resp.status_code == 200
        assert "owner" in resp.json()["searches"][0]["search"]["metadata"]
