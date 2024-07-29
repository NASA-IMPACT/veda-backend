"""
Test fixtures and data for STAC and Raster API integration testing.
"""

import pytest

SEEDED_COLLECTION = "noaa-emergency-response"
SEEDED_ID = "20200307aC0853900w361030"
STAC_ENDPOINT = "http://0.0.0.0:8081"
INDEX_ENDPOINT = "index.html"
DOCS_ENDPOINT = "docs"
STAC_HEALTH_ENDPOINT = "_mgmt/ping"
STAC_SEARCH_ENDPOINT = "search"
COLLECTIONS_ENDPOINT = "collections"

RASTER_ENDPOINT = "http://0.0.0.0:8082"
RASTER_HEALTH_ENDPOINT = "healthz"
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
def stac_search_endpoint():
    """
    Fixture providing a search endpoint url for integration testing of STAC api.

    Returns:
        string: A valid url.
    """
    return STAC_SEARCH_ENDPOINT
  
@pytest.fixture
def index_endpoint():
    """
    Fixture providing a index endpoint url for integration testing.

    Returns:
        string: A valid url.
    """
    return INDEX_ENDPOINT
  
@pytest.fixture
def docs_endpoint():
    """
    Fixture providing a docs endpoint url for integration testing.

    Returns:
        string: A valid url.
    """
    return DOCS_ENDPOINT
  
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
def collections_endpoint():
    """
    Fixture providing a collections endpoint url for integration testing.

    Returns:
        string: A valid url
    """
    return COLLECTIONS_ENDPOINT
  
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