"""test veda-backend STAC."""

import httpx

seeded_collection = "noaa-emergency-response"
stac_endpoint = "http://0.0.0.0:8081"
index_endpoint = "index.html"
docs_endpoint = "docs"
health_endpoint = "_mgmt/ping"
search_endpoint = "search"


def test_stac_health():
    """test stac health endpoint."""
    # Ping
    assert httpx.get(f"{stac_endpoint}/{health_endpoint}").status_code == 200


def test_stac_viewer():
    """test stac viewer."""
    resp = httpx.get(f"{stac_endpoint}/{index_endpoint}")
    assert resp.status_code == 200
    assert resp.headers.get("x-correlation-id") == "local"
    assert "<title>Simple STAC API Viewer</title>" in resp.text


def test_stac_docs():
    """test stac docs."""
    resp = httpx.get(f"{stac_endpoint}/{docs_endpoint}")
    assert resp.status_code == 200
    assert "Swagger UI" in resp.text


def test_stac_get_search():
    """test stac get search."""
    default_limit_param = "?limit=10"
    resp = httpx.get(f"{stac_endpoint}/{search_endpoint}{default_limit_param}")
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert len(features) > 0
    collections = [c["collection"] for c in features]
    assert seeded_collection in collections


def test_stac_post_search():
    """test stac post search."""
    request_body = {"collections": [seeded_collection]}
    resp = httpx.post(f"{stac_endpoint}/{search_endpoint}", json=request_body)
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert len(features) > 0
    collections = [c["collection"] for c in features]
    assert seeded_collection in collections


def test_stac_api():
    """test stac."""

    # Collections
    resp = httpx.get(f"{stac_endpoint}/collections")
    assert resp.status_code == 200
    collections = resp.json()["collections"]
    assert len(collections) > 0
    ids = [c["id"] for c in collections]
    assert "noaa-emergency-response" in ids

    # items
    resp = httpx.get(f"{stac_endpoint}/collections/noaa-emergency-response/items")
    assert resp.status_code == 200
    items = resp.json()["features"]
    assert len(items) == 10

    # item
    resp = httpx.get(
        f"{stac_endpoint}/collections/noaa-emergency-response/items/20200307aC0853300w361200"
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == "20200307aC0853300w361200"


def test_stac_to_raster():
    """test link to raster api."""
    # tilejson
    resp = httpx.get(
        f"{stac_endpoint}/collections/noaa-emergency-response/items/20200307aC0853300w361200/tilejson.json",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307

    # viewer
    resp = httpx.get(
        f"{stac_endpoint}/collections/noaa-emergency-response/items/20200307aC0853300w361200/viewer",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307
