"""
Test suite for STAC (SpatioTemporal Asset Catalog) Transactions API endpoints.

This module contains tests for the collection and item endpoints of the STAC API.
It verifies the behavior of the API when posting valid and invalid STAC collections and items,
as well as bulk items.

Endpoints tested:
- /collections
- /collections/{}/items
- /collections/{}/bulk_items
"""


collections_endpoint = "/collections"
items_endpoint = "/collections/{}/items"
bulk_endpoint = "/collections/{}/bulk_items"


class TestList:
    """
    Test cases for STAC API's collection and item endpoints.

    This class contains tests to ensure that the STAC API correctly handles
    posting valid and invalid STAC collections and items, both individually
    and in bulk. It uses pytest fixtures to set up the test environment with
    necessary data.
    """

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

    async def test_post_valid_collection(self, api_client, valid_stac_collection):
        """
        Test the API's response to posting a valid STAC collection.

        Asserts that the response status code is 200.
        """
        response = await api_client.post(
            collections_endpoint, json=valid_stac_collection
        )
        assert response.status_code == 201

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

    async def test_post_valid_item(self, api_client, valid_stac_item, collection_in_db):
        """
        Test the API's response to posting a valid STAC item.

        Asserts that the response status code is 200.
        """
        collection_id = valid_stac_item["collection"]
        response = await api_client.post(
            items_endpoint.format(collection_id), json=valid_stac_item
        )
        assert response.status_code == 201

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
