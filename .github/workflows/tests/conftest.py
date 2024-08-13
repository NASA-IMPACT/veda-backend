"""
Test fixtures and data for STAC and Raster API integration testing.
"""

import httpx
import pytest

SEEDED_COLLECTION = "noaa-emergency-response"
SEEDED_ID = "20200307aC0853900w361030"

COLLECTIONS_ROUTE = "collections"
INDEX_ROUTE = "index.html"
DOCS_ROUTE = "docs"
STAC_ENDPOINT = "http://0.0.0.0:8081"
STAC_HEALTH_ENDPOINT = "http://0.0.0.0:8081/_mgmt/ping"
SEARCH_ROUTE = "search"

RASTER_SEARCHES_ENDPOINT = "http://0.0.0.0:8082/searches"
RASTER_HEALTH_ENDPOINT = "http://0.0.0.0:8082/healthz"
TILEMATRIX = {"z": 15, "x": 8589, "y": 12849}

SEARCHES = [
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection1"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection2"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection3"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection4"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection5"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection6"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection7"],
        },
        "metadata": {"owner": "vincent"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection8"],
        },
        "metadata": {"owner": "sean"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection9"],
        },
        "metadata": {"owner": "sean"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection10"],
        },
        "metadata": {"owner": "drew"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection11"],
        },
        "metadata": {"owner": "drew"},
    },
    {
        "filter": {
            "op": "=",
            "args": [{"property": "collection"}, "collection12"],
        },
        "metadata": {"owner": "drew"},
    },
]


@pytest.fixture
def stac_endpoint():
    """
    Fixture providing a valid STAC url for integration testing.

    Returns:
        string: A valid STAC endpoint url.
    """
    return STAC_ENDPOINT


@pytest.fixture
def stac_health_endpoint():
    """
    Fixture providing a health endpoint url for integration testing.

    Returns:
        string: A valid url.
    """
    return STAC_HEALTH_ENDPOINT


@pytest.fixture
def search_route():
    """
    Fixture providing a search endpoint url for integration testing of STAC api.

    Returns:
        string: A valid url.
    """
    return SEARCH_ROUTE


@pytest.fixture
def index_route():
    """
    Fixture providing a index endpoint url for integration testing.

    Returns:
        string: A valid url.
    """
    return INDEX_ROUTE


@pytest.fixture
def docs_route():
    """
    Fixture providing a docs endpoint url for integration testing.

    Returns:
        string: A valid url.
    """
    return DOCS_ROUTE


@pytest.fixture
def seeded_collection():
    """
    Fixture providing a seeded collection in .github/workflows/data

    Returns:
        string: A collection
    """
    return SEEDED_COLLECTION


@pytest.fixture
def seeded_id():
    """
    Fixture providing a seeded collection id in .github/workflows/data

    Returns:
        string: A collection ID
    """
    return SEEDED_ID


@pytest.fixture
def collections_route():
    """
    Fixture providing a collections endpoint url for integration testing.

    Returns:
        string: A valid url
    """
    return COLLECTIONS_ROUTE


@pytest.fixture
def raster_endpoint():
    """
    Fixture providing a collections endpoint url for integration testing.

    Returns:
        string: A valid url
    """
    return RASTER_ENDPOINT


@pytest.fixture
def raster_health_endpoint():
    """
    Fixture providing a collections endpoint url for integration testing.

    Returns:
        string: A valid url
    """
    return RASTER_HEALTH_ENDPOINT


@pytest.fixture
def seeded_tilematrix():
    """
    Fixture providing a matrix of seeded data for integration testing.

    Returns:
        dict: A [z, x, y] set of dimensions
    """
    return TILEMATRIX


@pytest.fixture
def searches():
    """
    Fake searches to register

    Returns:
        dict: An array of searches
    """
    return SEARCHES


@pytest.fixture(scope="session")
def collection_schema():
    """Retrieve Collection Schema from

    Returns:
        String: A string representation of the yaml schema
    """
    response = httpx.get("https://api.stacspec.org/v1.0.0/collections/openapi.yaml")
    content = response.text
    return content


@pytest.fixture(scope="session")
def feature_schema():
    """Retrieve Feature Schema from

    Returns:
        String: A string representation of the yaml schema
    """
    response = httpx.get("https://api.stacspec.org/v1.0.0/ogcapi-features/openapi.yaml")
    content = response.text
    return content
