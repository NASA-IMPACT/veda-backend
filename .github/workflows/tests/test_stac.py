"""test veda-backend STAC."""

import httpx
import requests
import yaml
from openapi_schema_validator import validate

with requests.get(
    "https://api.stacspec.org/v1.0.0/ogcapi-features/openapi.yaml", allow_redirects=True
) as response:
    # Convert bytes to string
    content = response.content.decode("utf-8")
    # Load the yaml
    feature_schema = yaml.safe_load(content)

with requests.get(
    "https://api.stacspec.org/v1.0.0/collections/openapi.yaml", allow_redirects=True
) as response:
    # Convert bytes to string
    content = response.content.decode("utf-8")
    # Load the yaml
    collection_schema = yaml.safe_load(content)


stac_endpoint = "http://0.0.0.0:8081"
seeded_collection = "nightlights-500m-daily"
seeded_item = "VNP46A2_V011_ny_2021-03-01_cog"


def test_stac_api():
    """test stac."""
    # Ping
    assert httpx.get(f"{stac_endpoint}/_mgmt/ping").status_code == 200

    # viewer
    assert httpx.get(f"{stac_endpoint}/index.html").status_code == 200

    # Collections
    resp = httpx.get(f"{stac_endpoint}/collections")
    assert resp.status_code == 200
    collections = resp.json()["collections"]
    assert len(collections) > 0
    validate(collections[0], collection_schema)
    ids = [c["id"] for c in collections]
    assert seeded_collection in ids

    # items
    resp = httpx.get(f"{stac_endpoint}/collections/{seeded_collection}/items")
    assert resp.status_code == 200
    items = resp.json()["features"]
    validate(items[0], feature_schema)
    assert len(items) == 10

    # item
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_item}"
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == seeded_item
    validate(item, feature_schema)


def test_stac_to_raster():
    """test link to raster api."""
    # tilejson
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_item}/tilejson.json",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307

    # viewer
    resp = httpx.get(
        f"{stac_endpoint}/collections/{seeded_collection}/items/{seeded_item}/viewer",
        params={"assets": "cog"},
    )
    assert resp.status_code == 307
