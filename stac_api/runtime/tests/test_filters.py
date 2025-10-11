"""
Test suite for tenant filtering.

This module contains tests for the tenant filtering in the STAC API.
"""

import pytest


@pytest.mark.parametrize(
    "endpoint,expected_status,expected_property",
    [
        # Collection listed with tenant
        (
            "/{VALID_TENANT_ID}/collections",
            200,
            {"numberMatched": 1},
        ),
        # Collection listed without tenant
        (
            "/collections",
            200,
            {"numberMatched": 1},
        ),
        # Collection not listed with other tenant
        (
            "/{INVALID_TENANT_ID}/collections",
            200,
            {"numberMatched": 0},
        ),
        # Collection available with tenant
        (
            "/{VALID_TENANT_ID}/collections/barc-thomasfire",
            200,
            {"id": "barc-thomasfire"},
        ),
        # Collection available without tenant
        ("/collections/barc-thomasfire/items", 200, {"id": "barc-thomasfire"}),
        # Collection not available with other tenant
        (
            "/{INVALID_TENANT_ID}/collections/barc-thomasfire",
            404,
            {"code": "NotFoundError"},
        ),
        # Items available with tenant
        (
            "/{VALID_TENANT_ID}/collections/barc-thomasfire/items",
            200,
            {"numberMatched": 1},
        ),
        # Items available without tenant
        ("/collections/barc-thomasfire/items", 200, {"numberMatched": 1}),
        # Items not available with other tenant
        (
            "/{INVALID_TENANT_ID}/collections/barc-thomasfire/items",
            200,
            {"numberMatched": 0},
        ),
        # Items searchable with tenant
        (
            "/{VALID_TENANT_ID}/search",
            200,
            {"numberMatched": 1},
        ),
        # Items searchable without tenant
        (
            "/search",
            200,
            {"numberMatched": 1},
        ),
        # Items not searchable with other tenant
        (
            "/{INVALID_TENANT_ID}/search",
            200,
            {"numberMatched": 0},
        ),
    ],
)
async def test_proxy_filters(
    api_client,
    collection_items_in_db,
    test_tenant,
    endpoint,
    expected_status,
    expected_property,
):
    """
    Test the tenant filtering in the STAC API.
    """
    endpoint = endpoint.replace("{VALID_TENANT_ID}", test_tenant)
    endpoint = endpoint.replace("{INVALID_TENANT_ID}", "invalid-tenant")
    response = await api_client.get(f"{endpoint}")
    assert response.status_code == expected_status
    for key, value in expected_property.items():
        assert response.json()[key] == value
