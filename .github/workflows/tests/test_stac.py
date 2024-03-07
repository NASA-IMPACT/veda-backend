"""test veda-backend STAC."""

import httpx
from openapi_schema_validator import validate

stac_endpoint = "http://0.0.0.0:8081"


feature_schema = {
    "type": "object",
    "required": ["id", "bbox", "type", "links", "stac_version", "stac_extensions"],
    "properties": {
        "id": {"type": "string"},
        "bbox": {"type": "array"},
        "type": {"type": "string"},
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "type": {"type": "string"},
                    "href": {"type": "string"},
                },
            },
        },
        "assets": {"type": "object"},
        "geometry": {
            "type": "object",
            "properties": {"type": {"type": "string", "coordinates": "array"}},
        },
        "collection": {"type": "string"},
        "properties": {"type": "object"},
        "stac_version": {"type": "string"},
        "stac_extensions": {"type": "array"},
    },
}

collection_schema = {
    "type": "object",
    "required": [
        "stac_version",
        # "type",
        "id",
        "description",
        "license",
        "extent",
        "links",
    ],
    "properties": {
        "stac_version": {"type": "string"},
        "type": {"type": "string", "enum": ["Collection"]},
        "id": {
            "type": "string",
        },
        "description": {
            "type": "string",
            "description": "Detailed multi-line description to fully explain the catalog or collection.\n[CommonMark 0.29](http://commonmark.org/) syntax MAY be used for rich text representation.",
        },
        "keywords": {
            "type": "array",
            "description": "List of keywords describing the collection.",
            "items": {"type": "string"},
        },
        "license": {"type": "string"},
        "extent": {
            "type": "object",
            "required": ["spatial", "temporal"],
            "properties": {
                "spatial": {
                    "type": "object",
                    "required": ["bbox"],
                    "properties": {
                        "bbox": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "array",
                                "minItems": 4,
                                "maxItems": 6,
                                "items": {"type": "number"},
                            },
                        }
                    },
                },
                "temporal": {
                    "type": "object",
                    "required": ["interval"],
                    "properties": {
                        "interval": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "string",
                                    "format": "date-time",
                                    "nullable": "true",
                                },
                            },
                        },
                    },
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["href", "rel"],
                        "properties": {
                            "href": {"type": "string", "format": "uri"},
                            "rel": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


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
    assert "noaa-emergency-response" in ids

    # items
    resp = httpx.get(f"{stac_endpoint}/collections/noaa-emergency-response/items")
    assert resp.status_code == 200
    items = resp.json()["features"]
    validate(items[0], feature_schema)
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
