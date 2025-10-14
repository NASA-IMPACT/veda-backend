"""test veda-backend STAC."""

import httpx
import pytest
import yaml
from openapi_schema_validator import validate


class TestList:
    """
    Test cases for STAC API.

    This class contains integration tests to ensure that the STAC API functions correctly

    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        collections_route,
        docs_route,
        index_route,
        search_route,
        seeded_collection,
        seeded_id,
        stac_endpoint,
        stac_health_endpoint,
        collection_schema,
        feature_schema,
    ):
        """
        Set up the test environment with the required fixtures.
        """
        self.collections_route = collections_route
        self.docs_route = docs_route
        self.index_route = index_route
        self.search_route = search_route
        self.seeded_collection = seeded_collection
        self.seeded_id = seeded_id
        self.stac_endpoint = stac_endpoint
        self.stac_health_endpoint = stac_health_endpoint
        self.collection_schema = collection_schema
        self.feature_schema = feature_schema

    def test_stac_health(self):
        """test stac health endpoint."""
        assert httpx.get(self.stac_health_endpoint).status_code == 200

    def test_stac_viewer(self):
        """test stac viewer."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.index_route}")
        assert resp.status_code == 200
        assert resp.headers.get("x-correlation-id") == "local"
        assert "<title>Simple STAC API Viewer</title>" in resp.text

    def test_stac_docs(self):
        """test stac docs."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.docs_route}")
        assert resp.status_code == 200
        assert "Swagger UI" in resp.text

    def test_stac_get_search(self):
        """test stac get search."""
        default_limit_param = "?limit=10"
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.search_route}{default_limit_param}"
        )
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) > 0
        collections = [c["collection"] for c in features]
        assert self.seeded_collection in collections

    def test_stac_post_search(self):
        """test stac post search."""
        request_body = {"collections": [self.seeded_collection]}
        resp = httpx.post(
            f"{self.stac_endpoint}/{self.search_route}", json=request_body
        )
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) > 0
        collections = [c["collection"] for c in features]
        assert self.seeded_collection in collections

    def test_stac_get_collections(self):
        """test stac get collections"""
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}")
        assert resp.status_code == 200
        collections = resp.json()["collections"]
        assert len(collections) > 0
        id = [c["id"] for c in collections]
        assert self.seeded_collection in id

    def test_stac_get_collections_by_id(self):
        """test stac get collection by id"""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}"
        )
        assert resp.status_code == 200
        collection = resp.json()
        assert collection["id"] == self.seeded_collection

    def test_stac_get_collection_items_by_id(self):
        """test stac get items in collection by collection id"""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items"
        )
        assert resp.status_code == 200
        collection = resp.json()
        assert collection["type"] == "FeatureCollection"

    def test_stac_api(self):
        """test stac."""

        # Collections
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}")
        assert resp.status_code == 200
        collections = resp.json()["collections"]
        assert len(collections) > 0
        validate(collections[0], yaml.safe_load(self.collection_schema))
        ids = [c["id"] for c in collections]
        assert self.seeded_collection in ids

        # items
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items"
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        validate(items[0], yaml.safe_load(self.feature_schema))
        assert len(items) == 10

        # item
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}"
        )
        assert resp.status_code == 200
        item = resp.json()
        assert item["id"] == self.seeded_id
        validate(item, yaml.safe_load(self.feature_schema))

    def test_stac_to_raster(self):
        """test link to raster api."""
        tile_matrix_set_id = "WebMercatorQuad"

        # tilejson
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}/{tile_matrix_set_id}/tilejson.json",
            params={"assets": "cog"},
        )
        assert resp.status_code == 307

        # viewer
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{self.seeded_collection}/items/{self.seeded_id}/viewer",
            params={"assets": "cog"},
        )
        assert resp.status_code == 307


class TestTenantFiltering:
    """
    Test cases for STAC API tenant filtering.

    This class contains integration tests to ensure that tenant filtering works correctly
    with the collections and items loaded in the test environment.
    """

    from conftest import TENANT_COLLECTIONS

    @pytest.fixture(autouse=True)
    def setup(
        self,
        collections_route,
        search_route,
        stac_endpoint,
        tenant_collections,
    ):
        """
        Set up the test environment with the required fixtures.
        """
        self.collections_route = collections_route
        self.search_route = search_route
        self.stac_endpoint = stac_endpoint
        self.tenant_collections = tenant_collections

    @pytest.mark.parametrize(
        "tenant, tenant_collections",
        [
            (tenant, collections)
            for tenant, collections in TENANT_COLLECTIONS.items()
            if tenant
        ],
    )
    def test_collections_listed_with_tenant(self, tenant, tenant_collections):
        """Tenant collections should be listed when accessed with valid tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/{tenant}/collections")
        assert resp.status_code == 200
        assert set(c["id"] for c in resp.json()["collections"]) == set(
            tenant_collections
        )

    def test_collections_listed_without_tenant(self):
        """All collections should be listed when accessed without tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}")
        assert resp.status_code == 200

        all_collections = set()
        for collections in self.tenant_collections.values():
            all_collections.update(collections)

        assert set(c["id"] for c in resp.json()["collections"]) == all_collections

    def test_collections_not_listed_with_invalid_tenant(self):
        """No collections should be listed when accessed with invalid tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/invalid-tenant/collections")
        assert resp.status_code == 200
        assert resp.json()["collections"] == []

    @pytest.mark.parametrize(
        "tenant, collection",
        [
            (tenant, collection)
            for tenant, collections in TENANT_COLLECTIONS.items()
            for collection in collections
            if tenant
        ],
    )
    def test_collection_available_with_tenant(self, tenant, collection):
        """A tenant's collection should be available when accessed with that tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/{tenant}/collections/{collection}")
        assert resp.status_code == 200
        assert resp.json()["id"] == collection

    @pytest.mark.parametrize(
        "collection",
        set(
            collection
            for collections in TENANT_COLLECTIONS.values()
            for collection in collections
        ),
    )
    def test_collection_available_without_tenant(self, collection):
        """Any collection should be available when accessed without tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/{self.collections_route}/{collection}")
        assert resp.status_code == 200
        assert resp.json()["id"] == collection

    @pytest.mark.parametrize(
        "collection",
        set(
            collection
            for collections in TENANT_COLLECTIONS.values()
            for collection in collections
        ),
    )
    def test_collection_not_available_with_invalid_tenant(self, collection):
        """No collection should be returned when accessed with invalid tenant."""
        resp = httpx.get(
            f"{self.stac_endpoint}/invalid-tenant/collections/{collection}"
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "NotFoundError"

    @pytest.mark.parametrize(
        "tenant, collection",
        [
            (tenant, collection)
            for tenant, collections in TENANT_COLLECTIONS.items()
            for collection in collections
            if tenant
        ],
    )
    def test_items_available_with_tenant(self, tenant, collection):
        """Items should be available when accessed with valid tenant."""
        resp = httpx.get(
            f"{self.stac_endpoint}/{tenant}/collections/{collection}/items"
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) > 0
        # Should find items from the noaa-emergency-response collection
        for item in items:
            assert item["collection"] == collection

    @pytest.mark.parametrize(
        "collection",
        set(
            collection
            for collections in TENANT_COLLECTIONS.values()
            for collection in collections
        ),
    )
    def test_items_available_without_tenant(self, collection):
        """All collection's items should be available when accessed without tenant."""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.collections_route}/{collection}/items"
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) > 0
        for item in items:
            assert item["collection"] == collection

    @pytest.mark.parametrize(
        "collection",
        set(
            collection
            for collections in TENANT_COLLECTIONS.values()
            for collection in collections
        ),
    )
    def test_items_not_available_with_invalid_tenant(self, collection):
        """No collection's items should be returned when accessed with invalid tenant."""
        resp = httpx.get(
            f"{self.stac_endpoint}/invalid-tenant/collections/{collection}/items"
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) == 0

    @pytest.mark.parametrize(
        "tenant,tenant_collections",
        [
            (tenant, collections)
            for tenant, collections in TENANT_COLLECTIONS.items()
            if tenant
        ],
    )
    def test_search_with_tenant(self, tenant, tenant_collections):
        """Search with a tenant should return only items from that tenant's collections."""
        resp = httpx.get(f"{self.stac_endpoint}/{tenant}/search")
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) > 0
        for item in items:
            assert item["collection"] in tenant_collections

    def test_search_without_tenant(self):
        """Search without a tenant should return all collections."""
        resp = httpx.get(
            f"{self.stac_endpoint}/{self.search_route}", params={"limit": 1000}
        )
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) > 0
        # Should find items from all collections
        assert set(item["collection"] for item in items) == set(
            collection
            for collections in self.tenant_collections.values()
            for collection in collections
        )

    def test_search_not_available_with_invalid_tenant(self):
        """Search should return no items when accessed with invalid tenant."""
        resp = httpx.get(f"{self.stac_endpoint}/invalid-tenant/search")
        assert resp.status_code == 200
        items = resp.json()["features"]
        assert len(items) == 0

    @pytest.mark.parametrize(
        "tenant",
        [tenant for tenant in TENANT_COLLECTIONS.keys() if tenant],
    )
    def test_tenant_isolation(self, tenant):
        """Tenants should not be able to access each other's collections or items."""
        # emergency should not see barc-thomasfire
        resp = httpx.get(f"{self.stac_endpoint}/{tenant}/collections")
        assert resp.status_code == 200

        other_tenants_collections = set()
        for tenant_name, collections in self.tenant_collections.items():
            if tenant_name != tenant:
                other_tenants_collections.update(collections)

        forbidden_collections = set(other_tenants_collections) - set(
            self.tenant_collections[tenant]
        )
        collections = resp.json()["collections"]
        for collection in collections:
            assert collection["id"] not in forbidden_collections

        for collection in forbidden_collections:
            resp = httpx.get(f"{self.stac_endpoint}/{tenant}/collections/{collection}")
            assert resp.status_code == 404
            assert resp.json()["code"] == "NotFoundError"

            resp = httpx.get(
                f"{self.stac_endpoint}/{tenant}/collections/{collection}/items"
            )
            assert resp.status_code == 200
            assert resp.json()["features"] == []
