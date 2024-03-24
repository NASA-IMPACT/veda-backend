"""test veda-backend.raster."""

import httpx

raster_endpoint = "http://0.0.0.0:8082"
seeded_collection = "nightlights-500m-daily"
seeded_item = "VNP46A2_V011_ny_2021-03-01_cog"
seeded_item_bounds = [-80.0, 40.0, -70.0, 50.0]


def test_raster_api():
    """test api."""
    # health
    resp = httpx.get(
        f"{raster_endpoint}/healthz", headers={"Accept-Encoding": "br, gzip"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert resp.headers["content-encoding"] in ["br", "gzip"]


def test_mosaic_api():
    """test mosaic."""
    query = {"collections": [seeded_collection], "filter-lang": "cql-json"}
    resp = httpx.post(f"{raster_endpoint}/mosaic/register", json=query)
    assert resp.headers["content-type"] == "application/json"
    assert resp.status_code == 200
    assert resp.json()["searchid"]
    assert resp.json()["links"]

    searchid = resp.json()["searchid"]

    resp = httpx.get(
        f"{raster_endpoint}/mosaic/{searchid}/{str(seeded_item_bounds[0])},{str(seeded_item_bounds[1])}/assets"
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
    assert resp.json()[0]["id"] == seeded_item

    resp = httpx.get(f"{raster_endpoint}/mosaic/{searchid}/tiles/0/0/0/assets")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    assert list(resp.json()[0]) == ["id", "bbox", "assets", "collection"]
    items = resp.json()
    ids = [c["id"] for c in items]
    assert seeded_item in ids


def test_mosaic_search():
    """test mosaic."""
    # register some fake mosaic
    searches = [
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection1"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection2"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection3"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection4"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection5"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection6"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection7"]},
            "metadata": {"owner": "vincent"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection8"]},
            "metadata": {"owner": "sean"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection9"]},
            "metadata": {"owner": "sean"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection10"]},
            "metadata": {"owner": "drew"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection11"]},
            "metadata": {"owner": "drew"},
        },
        {
            "filter": {"op": "=", "args": [{"property": "collection"}, "collection12"]},
            "metadata": {"owner": "drew"},
        },
    ]
    for search in searches:
        resp = httpx.post(f"{raster_endpoint}/mosaic/register", json=search)
        assert resp.status_code == 200
        assert resp.json()["searchid"]

    resp = httpx.get(f"{raster_endpoint}/mosaic/list")
    assert resp.headers["content-type"] == "application/json"
    assert resp.status_code == 200
    assert (
        resp.json()["context"]["matched"] > 10
    )  # there should be at least 12 mosaic registered
    assert resp.json()["context"]["returned"] == 10  # default limit is 10

    # Make sure all mosaics returned have
    for mosaic in resp.json()["searches"]:
        assert mosaic["search"]["metadata"]["type"] == "mosaic"

    links = resp.json()["links"]
    assert len(links) == 2
    assert links[0]["rel"] == "self"
    assert links[1]["rel"] == "next"
    assert links[1]["href"] == f"{raster_endpoint}/mosaic/list?limit=10&offset=10"

    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"limit": 1, "offset": 1})
    assert resp.status_code == 200
    assert resp.json()["context"]["matched"] > 10
    assert resp.json()["context"]["limit"] == 1
    assert resp.json()["context"]["returned"] == 1

    links = resp.json()["links"]
    assert len(links) == 3
    assert links[0]["rel"] == "self"
    assert links[0]["href"] == f"{raster_endpoint}/mosaic/list?limit=1&offset=1"
    assert links[1]["rel"] == "next"
    assert links[1]["href"] == f"{raster_endpoint}/mosaic/list?limit=1&offset=2"
    assert links[2]["rel"] == "prev"
    assert links[2]["href"] == f"{raster_endpoint}/mosaic/list?limit=1&offset=0"

    # Filter on mosaic metadata
    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"owner": "vincent"})
    assert resp.status_code == 200
    assert resp.json()["context"]["matched"] == 7
    assert resp.json()["context"]["limit"] == 10
    assert resp.json()["context"]["returned"] == 7

    # sortBy
    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"sortby": "lastused"})
    assert resp.status_code == 200

    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"sortby": "usecount"})
    assert resp.status_code == 200

    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"sortby": "-owner"})
    assert resp.status_code == 200
    assert (
        "owner" not in resp.json()["searches"][0]["search"]["metadata"]
    )  # some mosaic don't have owners

    resp = httpx.get(f"{raster_endpoint}/mosaic/list", params={"sortby": "owner"})
    assert resp.status_code == 200
    assert "owner" in resp.json()["searches"][0]["search"]["metadata"]


def test_item():
    """test stac endpoints."""
    resp = httpx.get(
        f"{raster_endpoint}/stac/assets",
        params={
            "collection": seeded_collection,
            "item": seeded_item,
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert resp.json() == ["cog_default"]

    resp = httpx.get(
        f"{raster_endpoint}/stac/tilejson.json",
        params={
            "collection": seeded_collection,
            "item": seeded_item,
            "assets": "cog_default",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert resp.json()["tilejson"]
    assert "assets=cog" in resp.json()["tiles"][0]
    assert f"item={seeded_item}" in resp.json()["tiles"][0]
    assert f"collection={seeded_collection}" in resp.json()["tiles"][0]
    assert resp.json()["bounds"] == seeded_item_bounds
