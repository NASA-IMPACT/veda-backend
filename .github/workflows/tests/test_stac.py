"""test veda-backend STAC."""

import httpx

seeded_collection = "noaa-emergency-response"
seeded_id = "20200307aC0853300w361200"
stac_endpoint = "http://0.0.0.0:8081"
index_endpoint = "index.html"
docs_endpoint = "docs"
health_endpoint = "_mgmt/ping"
search_endpoint = "search"
collections_endpoint = "collections"


def test_stac_health():
    """test stac health endpoint."""

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


def test_stac_get_collections():
    """test stac get collections"""
    resp = httpx.get(f"{stac_endpoint}/{collections_endpoint}")
    assert resp.status_code == 200
    collections = resp.json()["collections"]
    assert len(collections) > 0
    id = [c["id"] for c in collections]
    assert seeded_collection in id


def test_stac_get_collections_by_id():
    """test stac get collection by id"""
    resp = httpx.get(f"{stac_endpoint}/{collections_endpoint}/{seeded_collection}")
    assert resp.status_code == 200
    collection = resp.json()
    assert collection["id"] == seeded_collection


def test_stac_get_collection_items_by_id():
    """test stac get items in collection by collection id"""
    resp = httpx.get(
        f"{stac_endpoint}/{collections_endpoint}/{seeded_collection}/items"
    )
    assert resp.status_code == 200
    collection = resp.json()
    assert collection["type"] == "FeatureCollection"


def test_stac_api():
    """test stac."""

    # Collections
    resp = httpx.get(f"{stac_endpoint}/collections")
    assert resp.status_code == 200
    collections = resp.json()["collections"]
    assert len(collections) > 0
    ids = [c["id"] for c in collections]
    assert seeded_collection in ids

    # items
    resp = httpx.get(f"{stac_endpoint}/collections/{seeded_collection}/items")
    assert resp.status_code == 200
    items = resp.json()["features"]
    assert len(items) == 10

    # item
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_id}"
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == seeded_id


def test_stac_to_raster():
    """test link to raster api."""
    # tilejson
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_id}/tilejson.json",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307

    # viewer
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_id}/viewer",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307
