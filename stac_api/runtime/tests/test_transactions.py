import pytest


collections_endpoint = "/collections"
items_endpoint = "/collections/{}/items"
bulk_endpoint = "/collections/{}/bulk_items"


class TestList:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        api_client,
        valid_stac_collection,
        valid_stac_item,
        invalid_stac_collection,
        invalid_stac_item
    ):
        self.api_client = api_client
        self.valid_stac_collection = valid_stac_collection
        self.valid_stac_item = valid_stac_item
        self.invalid_stac_collection = invalid_stac_collection
        self.invalid_stac_item = invalid_stac_item

    def test_post_invalid_collection(self):
        response = self.api_client.post(collections_endpoint, json=self.invalid_stac_collection)
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    def test_post_valid_collection(self):
        response = self.api_client.post(collections_endpoint, json=self.valid_stac_collection)
        # assert response.json() == {}
        assert response.status_code == 200

    def test_post_invalid_item(self):
        response = self.api_client.post(items_endpoint.format(self.invalid_stac_item["collection"]), json=self.invalid_stac_item)
        assert response.json()["detail"] == "Validation Error"
        assert response.status_code == 422

    def test_post_valid_item(self):
        response = self.api_client.post(items_endpoint.format(self.valid_stac_item["collection"]), json=self.valid_stac_item)
        # assert response.json() == {}
        assert response.status_code == 200

    def test_post_invalid_bulk_items(self):
        item_id = self.invalid_stac_item["id"]
        collection_id = self.invalid_stac_item["collection"]
        invalid_request = {
            "items": {
                item_id: self.invalid_stac_item
            },
            "method": "upsert"
        }
        response = self.api_client.post(bulk_endpoint.format(collection_id), json=invalid_request)
        assert response.status_code == 422

    def test_post_valid_bulk_items(self):
        item_id = self.valid_stac_item["id"]
        collection_id = self.valid_stac_item["collection"]
        valid_request = {
            "items": {
                item_id: self.valid_stac_item
            },
            "method": "upsert"
        }
        response = self.api_client.post(bulk_endpoint.format(collection_id), json=valid_request)
        assert response.status_code == 422
