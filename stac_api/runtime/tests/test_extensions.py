"""
Test suite for STAC (SpatioTemporal Asset Catalog) Extensions including Transactions and Collections Search API endpoints.

This module contains tests for the collection and item endpoints of the STAC API.
It verifies the behavior of the API when posting valid and invalid STAC collections and items,
as well as bulk items.

Endpoints tested:
Transactions
- /collections
- /collections/{}/items
- /collections/{}/bulk_items

Collection Search
This module adds search options to collections GET method
- /Collections search by id and free text search

"""
import pytest

collections_endpoint = "/collections"
items_endpoint = "/collections/{}/items"
bulk_endpoint = "/collections/{}/bulk_items"
tenant_collections_endpoint = "/fake-tenant/collections"


class TestList:
    """
    Test cases for STAC API's collection and item endpoints.

    This class contains tests to ensure that the STAC API correctly handles
    posting valid and invalid STAC collections and items, both individually
    and in bulk. It uses pytest fixtures to set up the test environment with
    necessary data.
    """

    @pytest.mark.asyncio
    async def test_post_invalid_collection(self, api_client, invalid_stac_collection):
        """
        Test the API's response to posting an invalid STAC collection.

        Asserts that the response status code is 422 and the detail
        is "Validation Error".
        """
        response = await api_client.post(
            collections_endpoint, json=invalid_stac_collection
        )
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_valid_collection(self, api_client, valid_stac_collection):
        """
        Test the API's response to posting a valid STAC collection.

        Asserts that the response status code is 200.
        """
        response = await api_client.post(
            collections_endpoint, json=valid_stac_collection
        )
        assert response.status_code in [201, 409]

    @pytest.mark.asyncio
    async def test_post_invalid_item(self, api_client, invalid_stac_item):
        """
        Test the API's response to posting an invalid STAC item.

        Asserts that the response status code is 422 and the detail
        is "Validation Error".
        """
        collection_id = invalid_stac_item["collection"]
        response = await api_client.post(
            items_endpoint.format(collection_id), json=invalid_stac_item
        )
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_valid_item(self, api_client, valid_stac_item, collection_in_db):
        """
        Test the API's response to posting a valid STAC item.

        Asserts that the response status code is 200.
        """
        collection_id = collection_in_db["regular_collection"]
        item_data = valid_stac_item.copy()
        item_data["collection"] = collection_id

        response = await api_client.post(
            items_endpoint.format(collection_id), json=valid_stac_item
        )
        assert response.status_code in [201, 409]  # 201 for new, 409 for existing

    @pytest.mark.asyncio
    async def test_post_invalid_bulk_items(self, api_client, invalid_stac_item):
        """
        Test the API's response to posting invalid bulk STAC items.

        Asserts that the response status code is 422.
        """
        item_id = invalid_stac_item["id"]
        collection_id = invalid_stac_item["collection"]
        invalid_request = {"items": {item_id: invalid_stac_item}, "method": "upsert"}

        response = await api_client.post(
            bulk_endpoint.format(collection_id), json=invalid_request
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_valid_bulk_items(
        self, api_client, valid_stac_item, collection_in_db
    ):
        """
        Test the API's response to posting valid bulk STAC items.

        Asserts that the response status code is 200.
        """
        item_id = valid_stac_item["id"]
        collection_id = valid_stac_item["collection"]
        valid_request = {"items": {item_id: valid_stac_item}, "method": "upsert"}

        response = await api_client.post(
            bulk_endpoint.format(collection_id), json=valid_request
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_collection_by_id(self, api_client, collection_in_db):
        """
        Test searching for a specific collection by its ID.
        """
        # The `collection_in_db` fixture ensures the collection exists and provides its ID.
        collection_id = collection_in_db["regular_collection"]

        response = await api_client.get(f"{collections_endpoint}/{collection_id}")

        assert response.status_code == 200

        response_data = response.json()

        assert response_data["id"] == collection_id

    @pytest.mark.asyncio
    async def test_collection_freetext_search_by_title(
        self, api_client, collection_in_db
    ):
        """
        Test free-text search for a collection using a word from its title.
        """

        # The `collection_in_db` fixture ensures the collection exists.
        collection_id = collection_in_db["regular_collection"]

        # Use a unique word from the collection's title for the query.
        search_term = "precipitation"

        # Perform a GET request with the `q` free-text search parameter.
        response = await api_client.get(collections_endpoint, params={"q": search_term})

        assert response.status_code == 200
        response_data = response.json()

        assert len(response_data["collections"]) > 0

        returned_ids = [col["id"] for col in response_data["collections"]]
        assert collection_id in returned_ids

    @pytest.mark.asyncio
    async def test_get_collections_by_tenant(self, api_client, collection_in_db):
        """
        Test searching for a specific collection by its ID.
        """
        collection_id = collection_in_db["tenant_collection"]

        # Perform a GET request to the /collections endpoint with a tenant
        response = await api_client.get(
            tenant_collections_endpoint,
        )

        assert response.status_code == 200

        response_data = response.json()

        assert response_data["collections"][0]["id"] == collection_id

    @pytest.mark.asyncio
    async def test_tenant_landing_page_customization(self, api_client):
        """
        Test that tenant landing page is properly customized for tenant
        """
        response = await api_client.get("/fake-tenant/")
        assert response.status_code == 200

        landing_page = response.json()
        assert "FAKE-TENANT" in landing_page["title"]

        excluded_rels = [
            "self",
            "root",
            "service-desc",
            "service-doc",
            "conformance",
            "queryables",
        ]
        for link in landing_page.get("links", []):
            rel = link.get("rel")
            href = link.get("href", "")

            # Check if rel should be excluded (exact match or contains "queryables")
            should_exclude = rel in excluded_rels or "queryables" in rel

            if should_exclude:
                assert (
                    "/fake-tenant/" not in href
                ), f"Excluded rel '{rel}' incorrectly contains tenant: {href}"
                print(f"Excluded rel '{rel}' correctly has no tenant: {href}")
            else:
                if href.startswith("/api/stac") or "api/stac" in href:
                    assert (
                        "/fake-tenant/" in href
                    ), f"Included rel '{rel}' does not have tenant: {href}"
                    print(f"Included rel '{rel}' correctly has tenant: {href}")

    @pytest.mark.asyncio
    async def test_get_collection_by_id_with_tenant(self, api_client, collection_in_db):
        """
        Test searching for a specific collection by its ID and tenant
        """
        # The `collection_in_db` fixture ensures the collection exists and provides its ID.
        collection_id = collection_in_db["tenant_collection"]

        # Perform a GET request to the /fake-tenant/collections endpoint with an "ids" query
        response = await api_client.get(
            tenant_collections_endpoint, params={"ids": collection_id}
        )

        assert response.status_code == 200

        response_data = response.json()

        assert response_data["collections"][0]["id"] == collection_id

    @pytest.mark.asyncio
    async def test_tenant_validation_error(self, api_client, collection_in_db):
        """
        Test that accessing wrong tenant's collection returns 404
        """
        collection_id = collection_in_db["tenant_collection"]

        # Try to access unexistent tenant for collection that exists in fake-tenant
        response = await api_client.get(f"/fake-tenant-2/collections/{collection_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_tenant_format(self, api_client):
        """
        Test handling of invalid tenant formats
        """

        # Non existent tenant should just show no collections
        response = await api_client.get("/invalid-tenant-format/collections")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            response_data = response.json()
            assert response_data["collections"] == []

    @pytest.mark.asyncio
    async def test_missing_tenant_parameter(self, api_client):
        """
        Test behavior when tenant parameter is not supplied in route path
        """

        response = await api_client.get("/collections")
        # Should return all collections (no tenant filtering)
        assert response.status_code == 200
