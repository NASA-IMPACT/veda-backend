"""
Test suite for tenant filtering.

This module contains tests for the tenant filtering in the STAC API.
"""

import pytest


@pytest.fixture
def invalid_tenant():
    """Fixture providing an invalid tenant ID for testing."""
    return "invalid-tenant"


async def test_collections_listed_with_tenant(
    api_client, collection_in_db, test_tenant
):
    """Test that collections are listed when accessed with valid tenant."""
    response = await api_client.get(f"/{test_tenant}/collections")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["collections"][0]["id"] == collection_in_db


async def test_collections_listed_without_tenant(api_client, collection_in_db):
    """Test that collections are listed when accessed without tenant."""
    response = await api_client.get("/collections")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["collections"][0]["id"] == collection_in_db


async def test_collections_not_listed_with_invalid_tenant(
    api_client, collection_in_db, invalid_tenant
):
    """Test that collections are not listed when accessed with invalid tenant."""
    response = await api_client.get(f"/{invalid_tenant}/collections")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 0
    assert response.json()["collections"] == []


async def test_collection_available_with_tenant(
    api_client, collection_in_db, test_tenant
):
    """Test that a specific collection is available when accessed with valid tenant."""
    response = await api_client.get(f"/{test_tenant}/collections/{collection_in_db}")
    assert response.status_code == 200
    assert response.json()["id"] == collection_in_db


async def test_collection_available_without_tenant(api_client, collection_in_db):
    """Test that a specific collection is available when accessed without tenant."""
    response = await api_client.get(f"/collections/{collection_in_db}")
    assert response.status_code == 200
    assert response.json()["id"] == collection_in_db


async def test_collection_not_available_with_invalid_tenant(
    api_client, collection_in_db, invalid_tenant
):
    """Test that a specific collection is not available when accessed with invalid tenant."""
    response = await api_client.get(f"/{invalid_tenant}/collections/{collection_in_db}")
    assert response.status_code == 404
    assert response.json()["code"] == "NotFoundError"


async def test_items_available_with_tenant(
    api_client, collection_in_db, collection_items_in_db, test_tenant
):
    """Test that items are available when accessed with valid tenant."""
    response = await api_client.get(
        f"/{test_tenant}/collections/{collection_in_db}/items"
    )
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["features"][0]["id"] == collection_items_in_db


async def test_items_available_without_tenant(
    api_client, collection_in_db, collection_items_in_db
):
    """Test that items are available when accessed without tenant."""
    response = await api_client.get(f"/collections/{collection_in_db}/items")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["features"][0]["id"] == collection_items_in_db


async def test_items_not_available_with_invalid_tenant(
    api_client, collection_in_db, collection_items_in_db, invalid_tenant
):
    """Test that items are not available when accessed with invalid tenant."""
    response = await api_client.get(
        f"/{invalid_tenant}/collections/{collection_in_db}/items"
    )
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 0
    assert response.json()["features"] == []


async def test_search_with_tenant(
    api_client, collection_in_db, collection_items_in_db, test_tenant
):
    """Test that search works when accessed with valid tenant."""
    response = await api_client.get(f"/{test_tenant}/search")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["features"][0]["id"] == collection_items_in_db


async def test_search_without_tenant(
    api_client, collection_in_db, collection_items_in_db
):
    """Test that search works when accessed without tenant."""
    response = await api_client.get("/search")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 1
    assert response.json()["features"][0]["id"] == collection_items_in_db


async def test_search_not_available_with_invalid_tenant(
    api_client, collection_in_db, collection_items_in_db, invalid_tenant
):
    """Test that search returns no results when accessed with invalid tenant."""
    response = await api_client.get(f"/{invalid_tenant}/search")
    assert response.status_code == 200
    assert response.json()["numberMatched"] == 0
    assert response.json()["features"] == []
