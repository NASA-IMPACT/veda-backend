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

import pytest

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

    @pytest.fixture(autouse=True)
    def setup(
        self,
        api_client,
        valid_stac_collection,
        valid_stac_item,
        invalid_stac_collection,
        invalid_stac_item,
    ):
        """
        Set up the test environment with the required fixtures.

        Args:
            api_client: The API client for making requests.
            valid_stac_collection: A valid STAC collection for testing.
            valid_stac_item: A valid STAC item for testing.
            invalid_stac_collection: An invalid STAC collection for testing.
            invalid_stac_item: An invalid STAC item for testing.
        """
        self.api_client = api_client
        self.valid_stac_collection = valid_stac_collection
        self.valid_stac_item = valid_stac_item
        self.invalid_stac_collection = invalid_stac_collection
        self.invalid_stac_item = invalid_stac_item

    def test_post_invalid_collection(self):
        """
        Test the API's response to posting an invalid STAC collection.

        Asserts that the response status code is 422 and the detail
        is "Validation Error".
        """
        response = self.api_client.post(
            collections_endpoint, json=self.invalid_stac_collection
        )
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    def test_post_valid_collection(self):
        """
        Test the API's response to posting a valid STAC collection.

        Asserts that the response status code is 200.
        """
        response = self.api_client.post(
            collections_endpoint, json=self.valid_stac_collection
        )
        # assert response.json() == {}
        assert response.status_code == 200

    def test_post_invalid_item(self):
        """
        Test the API's response to posting an invalid STAC item.

        Asserts that the response status code is 422 and the detail
        is "Validation Error".
        """
        response = self.api_client.post(
            items_endpoint.format(self.invalid_stac_item["collection"]),
            json=self.invalid_stac_item,
        )
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    def test_post_valid_item(self):
        """
        Test the API's response to posting a valid STAC item.

        Asserts that the response status code is 200.
        """
        response = self.api_client.post(
            items_endpoint.format(self.valid_stac_item["collection"]),
            json=self.valid_stac_item,
        )
        # assert response.json() == {}
        assert response.status_code == 200

    def test_post_invalid_bulk_items(self):
        """
        Test the API's response to posting invalid bulk STAC items.

        Asserts that the response status code is 422.
        """
        item_id = self.invalid_stac_item["id"]
        collection_id = self.invalid_stac_item["collection"]
        invalid_request = {
            "items": {item_id: self.invalid_stac_item},
            "method": "upsert",
        }
        response = self.api_client.post(
            bulk_endpoint.format(collection_id), json=invalid_request
        )
        assert response.status_code == 422

    def test_post_valid_bulk_items(self):
        """
        Test the API's response to posting valid bulk STAC items.

        Asserts that the response status code is 200.
        """
        item_id = self.valid_stac_item["id"]
        collection_id = self.valid_stac_item["collection"]
        valid_request = {"items": {item_id: self.valid_stac_item}, "method": "upsert"}
        response = self.api_client.post(
            bulk_endpoint.format(collection_id), json=valid_request
        )
        assert response.status_code == 200
