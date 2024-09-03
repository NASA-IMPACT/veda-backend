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


def test_post_invalid_collection(api_client, invalid_stac_collection):
    """
    Test the API's response to posting an invalid STAC collection.

    Asserts that the response status code is 422 and the detail
    is "Validation Error".
    """
    response = api_client.post(collections_endpoint, json=invalid_stac_collection)
    assert response.json()["detail"] == "Validation Error"
    assert response.status_code == 422


def test_post_valid_collection(api_client, valid_stac_collection):
    """
    Test the API's response to posting a valid STAC collection.

    Asserts that the response status code is 200.
    """
    response = api_client.post(collections_endpoint, json=valid_stac_collection)
    # assert response.json() == {}
    assert response.status_code == 200


def test_post_invalid_item(api_client, invalid_stac_item):
    """
    Test the API's response to posting an invalid STAC item.

    Asserts that the response status code is 422 and the detail
    is "Validation Error".
    """
    response = api_client.post(
        items_endpoint.format(invalid_stac_item["collection"]),
        json=invalid_stac_item,
    )
    assert response.json()["detail"] == "Validation Error"
    assert response.status_code == 422


def test_post_valid_item(api_client, valid_stac_item):
    """
    Test the API's response to posting a valid STAC item.

    Asserts that the response status code is 200.
    """
    response = api_client.post(
        items_endpoint.format(valid_stac_item["collection"]),
        json=valid_stac_item,
    )
    # assert response.json() == {}
    assert response.status_code == 200


def test_post_invalid_bulk_items(api_client, invalid_stac_item):
    """
    Test the API's response to posting invalid bulk STAC items.

    Asserts that the response status code is 422.
    """
    item_id = invalid_stac_item["id"]
    collection_id = invalid_stac_item["collection"]
    invalid_request = {
        "items": {item_id: invalid_stac_item},
        "method": "upsert",
    }
    response = api_client.post(
        bulk_endpoint.format(collection_id), json=invalid_request
    )
    assert response.status_code == 422


def test_post_valid_bulk_items(api_client, valid_stac_item):
    """
    Test the API's response to posting valid bulk STAC items.

    Asserts that the response status code is 200.
    """
    item_id = valid_stac_item["id"]
    collection_id = valid_stac_item["collection"]
    valid_request = {"items": {item_id: valid_stac_item}, "method": "upsert"}
    response = api_client.post(bulk_endpoint.format(collection_id), json=valid_request)
    assert response.status_code == 200
