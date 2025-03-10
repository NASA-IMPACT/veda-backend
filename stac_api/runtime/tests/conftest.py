"""
Test fixtures and data for STAC Transactions API testing.

This module contains fixtures and mock data used for testing the STAC API.
It includes valid and invalid STAC collections and items, as well as environment
setup for testing with mock AWS and PostgreSQL configurations.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from stac_fastapi.pgstac.db import close_db_connection, connect_to_db

VALID_COLLECTION = {
    "id": "CMIP245-winter-median-pr",
    "type": "Collection",
    "title": "Projected changes to winter (January, February, and March) cumulative daily precipitation",
    "links": [],
    "description": "Differences in winter (January, February, and March) cumulative daily precipitation between a historical period (1995 - 2014) and multiple 20-year periods from an ensemble of CMIP6 climate projections (SSP2-4.5) downscaled by NASA Earth Exchange (NEX-GDDP-CMIP6)",
    "extent": {
        "spatial": {"bbox": [[-126, 30, -104, 51]]},
        "temporal": {"interval": [["2025-01-01T00:00:00Z", "2085-03-31T12:00:00Z"]]},
    },
    "license": "MIT",
    "stac_extensions": [
        "https://stac-extensions.github.io/render/v1.0.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
    ],
    "item_assets": {
        "cog_default": {
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data", "layer"],
            "title": "Default COG Layer",
            "description": "Cloud optimized default layer to display on map",
        }
    },
    "dashboard:is_periodic": False,
    "dashboard:time_density": "year",
    "stac_version": "1.0.0",
    "renders": {
        "dashboard": {
            "resampling": "bilinear",
            "bidx": [1],
            "nodata": "nan",
            "colormap_name": "rdbu",
            "rescale": [[-60, 60]],
            "assets": ["cog_default"],
            "title": "VEDA Dashboard Render Parameters",
        }
    },
    "providers": [
        {
            "name": "NASA Center for Climate Simulation (NCCS)",
            "url": "https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6",
            "roles": ["producer", "processor", "licensor"],
        },
        {
            "name": "NASA VEDA",
            "url": "https://www.earthdata.nasa.gov/dashboard/",
            "roles": ["host"],
        },
    ],
    "assets": {
        "thumbnail": {
            "title": "Thumbnail",
            "description": "Photo by Justin Pflug (Photo of Nisqually glacier)",
            "href": "https://thumbnails.openveda.cloud/CMIP-winter-median.jpeg",
            "type": "image/jpeg",
            "roles": ["thumbnail"],
        }
    },
}

VALID_ITEM = {
    "id": "OMI_trno2_0.10x0.10_2023_Col3_V4",
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "type": "Feature",
    "links": [
        {
            "rel": "collection",
            "type": "application/json",
            "href": "https://dev.openveda.cloud/api/stac/collections/CMIP245-winter-median-pr",
        },
        {
            "rel": "parent",
            "type": "application/json",
            "href": "https://dev.openveda.cloud/api/stac/collections/CMIP245-winter-median-pr",
        },
        {
            "rel": "root",
            "type": "application/json",
            "href": "https://dev.openveda.cloud/api/stac/",
        },
        {
            "rel": "self",
            "type": "application/geo+json",
            "href": "https://dev.openveda.cloud/api/stac/collections/CMIP245-winter-median-pr/items/OMI_trno2_0.10x0.10_2023_Col3_V4",
        },
        {
            "title": "Map of Item",
            "href": "https://dev.openveda.cloud/api/raster/stac/map?collection=CMIP245-winter-median-pr&item=OMI_trno2_0.10x0.10_2023_Col3_V4&assets=cog_default&rescale=0%2C3000000000000000&colormap_name=reds",
            "rel": "preview",
            "type": "text/html",
        },
    ],
    "assets": {
        "no2": {
            "href": "s3://veda-data-store-staging/OMI_trno2-COG/OMI_trno2_0.10x0.10_2023_Col3_V4.tif",
            "type": "image/tiff; application=geotiff",
            "roles": ["data", "layer"],
            "title": "NO2 values",
            "proj:bbox": [-180.0, -90.0, 180.0, 90.0],
            "proj:epsg": 4326,
            "proj:wkt2": 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
            "proj:shape": [1800, 3600],
            "description": "description",
            "raster:bands": [
                {
                    "scale": 1.0,
                    "nodata": -1.2676506002282294e30,
                    "offset": 0.0,
                    "sampling": "area",
                    "data_type": "float32",
                    "histogram": {
                        "max": 14863169193246720,
                        "min": -2293753591103488.0,
                        "count": 11,
                        "buckets": [57, 484234, 23295, 2552, 694, 318, 230, 79, 42, 12],
                    },
                    "statistics": {
                        "mean": 365095923477877.9,
                        "stddev": 569167954388057.0,
                        "maximum": 14863169193246720,
                        "minimum": -2293753591103488.0,
                        "valid_percent": 97.56336212158203,
                    },
                }
            ],
            "proj:geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-180.0, -90.0],
                        [180.0, -90.0],
                        [180.0, 90.0],
                        [-180.0, 90.0],
                        [-180.0, -90.0],
                    ]
                ],
            },
            "proj:projjson": {
                "id": {"code": 4326, "authority": "EPSG"},
                "name": "WGS 84",
                "type": "GeographicCRS",
                "datum": {
                    "name": "World Geodetic System 1984",
                    "type": "GeodeticReferenceFrame",
                    "ellipsoid": {
                        "name": "WGS 84",
                        "semi_major_axis": 6378137,
                        "inverse_flattening": 298.257223563,
                    },
                },
                "$schema": "https://proj.org/schemas/v0.7/projjson.schema.json",
                "coordinate_system": {
                    "axis": [
                        {
                            "name": "Geodetic latitude",
                            "unit": "degree",
                            "direction": "north",
                            "abbreviation": "Lat",
                        },
                        {
                            "name": "Geodetic longitude",
                            "unit": "degree",
                            "direction": "east",
                            "abbreviation": "Lon",
                        },
                    ],
                    "subtype": "ellipsoidal",
                },
            },
            "proj:transform": [0.1, 0.0, -180.0, 0.0, -0.1, 90.0, 0.0, 0.0, 1.0],
        },
        "rendered_preview": {
            "title": "Rendered preview",
            "href": "https://dev.openveda.cloud/api/raster/stac/preview.png?collection=CMIP245-winter-median-pr&item=OMI_trno2_0.10x0.10_2023_Col3_V4&assets=cog_default&rescale=0%2C3000000000000000&colormap_name=reds",
            "rel": "preview",
            "roles": ["overview"],
            "type": "image/png",
        },
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
    },
    "collection": "CMIP245-winter-median-pr",
    "properties": {
        "end_datetime": "2023-12-31T00:00:00+00:00",
        "start_datetime": "2023-01-01T00:00:00+00:00",
        "datetime": None,
    },
    "stac_version": "1.0.0",
    "stac_extensions": [
        "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        "https://stac-extensions.github.io/projection/v1.1.0/schema.json",
    ],
}


@pytest.fixture(autouse=True)
def test_environ():
    """
    Set up the test environment with mocked AWS and PostgreSQL credentials.

    This fixture sets environment variables to mock AWS credentials and
    PostgreSQL database configuration for testing purposes.
    """
    # Mocked AWS Credentials for moto (best practice recommendation from moto)
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["VEDA_STAC_CLIENT_ID"] = "stac"
    os.environ[
        "VEDA_STAC_OPENID_CONFIGURATION_URL"
    ] = "https://auth.openveda.cloud/realms/veda/.well-known/openid-configuration"
    os.environ["VEDA_STAC_ENABLE_TRANSACTIONS"] = "True"

    # Config mocks
    os.environ["POSTGRES_USER"] = "username"
    os.environ["POSTGRES_PASS"] = "password"
    os.environ["POSTGRES_DBNAME"] = "postgis"
    os.environ["POSTGRES_HOST_READER"] = "0.0.0.0"
    os.environ["POSTGRES_HOST_WRITER"] = "0.0.0.0"
    os.environ["POSTGRES_PORT"] = "5432"


def override_validated_token():
    """
    Mock function to override validated token dependency.

    Returns:
        str: A fake token to bypass authorization in tests.
    """
    return "fake_token"


@pytest.fixture
async def app():
    """
    Fixture to initialize the FastAPI application.

    This fixture imports and returns the FastAPI application instance
    for testing purposes.

    Args:
        test_environ: A fixture setting up the test environment.

    Returns:
        FastAPI: The FastAPI application instance.
    """
    from src.app import app

    await connect_to_db(app)
    yield app
    await close_db_connection(app)


@pytest.fixture(scope="function")
async def api_client(app):
    """
    Fixture to initialize the API client for making requests.

    This fixture creates a TestClient instance for interacting with the
    FastAPI application, and sets up dependency overrides for testing.

    Args:
        app: A fixture providing the FastAPI application instance.

    Yields:
        TestClient: The TestClient instance for API testing.
    """
    from src.app import oidc_auth

    app.dependency_overrides[oidc_auth.valid_token_dependency] = override_validated_token
    base_url = "http://test"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=base_url
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def valid_stac_collection():
    """
    Fixture providing a valid STAC collection for testing.

    Returns:
        dict: A valid STAC collection.
    """
    return VALID_COLLECTION


@pytest.fixture
def invalid_stac_collection():
    """
    Fixture providing an invalid STAC collection for testing.

    Returns:
        dict: An invalid STAC collection with the 'extent' field removed.
    """
    invalid = VALID_COLLECTION.copy()
    invalid.pop("extent")
    return invalid


@pytest.fixture
def valid_stac_item():
    """
    Fixture providing a valid STAC item for testing.

    Returns:
        dict: A valid STAC item.
    """
    return VALID_ITEM


@pytest.fixture
def invalid_stac_item():
    """
    Fixture providing an invalid STAC item for testing.

    Returns:
        dict: An invalid STAC item with the 'properties' field removed.
    """
    invalid_item = VALID_ITEM.copy()
    invalid_item.pop("properties")
    return invalid_item
