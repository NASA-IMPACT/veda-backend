"""Tests for Resource Extractors

These tests verify that resource extractors correctly identify resources
from requests for authorization purposes.
"""

import json
from typing import Optional, cast

from veda_auth.resource_extractors import (
    _extract_collection_resource_id_from_post_body,
    _extract_tenant_from_body,
    extract_ingest_resource_id,
    extract_stac_resource_id,
)

from fastapi import Request
from starlette.datastructures import URL


class MockState:
    """Simple state object for MockRequest"""

    def __init__(
        self, tenant: Optional[str] = None, cached_body: Optional[bytes] = None
    ):
        """Initialize MockState with optional tenant and cached_body"""
        if tenant:
            self.tenant = tenant
        if cached_body:
            self._cached_body = cached_body


class MockRequest:
    """Mock FastAPI Request object for testing"""

    def __init__(
        self,
        path: str,
        method: str = "GET",
        tenant: Optional[str] = None,
        cached_body: Optional[bytes] = None,
    ):
        """Initialize MockRequest with path, method, and optional tenant/cached_body"""
        self.url = URL(path)
        self.method = method
        self.state = MockState(tenant=tenant, cached_body=cached_body)


class TestExtractTenantFromBody:
    """Test tenant extraction from request body"""

    def test_tenant_at_root_level(self):
        """Tenant at root level should be extracted"""
        body_data = {"id": "test-collection", "eic:tenant": "faketenant1"}
        tenant = _extract_tenant_from_body(body_data)
        assert tenant == "faketenant1"

    def test_tenant_in_properties(self):
        """Tenant in properties should be extracted"""
        body_data = {
            "id": "test-collection",
            "properties": {"eic:tenant": "faketenant2"},
        }
        tenant = _extract_tenant_from_body(body_data)
        assert tenant == "faketenant2"

    def test_tenant_at_root_takes_precedence(self):
        """If tenant exists at both root and properties, root takes precedence"""
        body_data = {
            "id": "test-collection",
            "eic:tenant": "faketenant1",
            "properties": {"eic:tenant": "faketenant2"},
        }
        tenant = _extract_tenant_from_body(body_data)
        assert tenant == "faketenant1"

    def test_no_tenant_returns_none(self):
        """Missing tenant should return None"""
        body_data = {"id": "test-collection"}
        tenant = _extract_tenant_from_body(body_data)
        assert tenant is None

    def test_custom_tenant_field(self):
        """Custom tenant field name should be respected"""
        body_data = {"id": "test-collection", "custom:tenant": "faketenant1"}
        tenant = _extract_tenant_from_body(body_data, tenant_field="custom:tenant")
        assert tenant == "faketenant1"

    def test_empty_tenant_returns_none(self):
        """Empty string tenant should return None"""
        body_data = {"id": "test-collection", "eic:tenant": ""}
        tenant = _extract_tenant_from_body(body_data)
        assert tenant is None

    def test_none_tenant_returns_none(self):
        """None tenant should return None"""
        body_data = {"id": "test-collection", "eic:tenant": None}
        tenant = _extract_tenant_from_body(body_data)
        assert tenant is None


class TestExtractCollectionResourceIdFromPostBody:
    """Test collection resource ID extraction from POST/PUT/PATCH body"""

    def test_collection_with_tenant(self):
        """Collection with tenant should return tenant-specific resource ID"""
        body_data = {"id": "test-collection", "eic:tenant": "faketenant1"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = _extract_collection_resource_id_from_post_body(
            cast(Request, request)
        )
        assert resource_id == "stac:collection:faketenant1:*"

    def test_collection_without_tenant(self):
        """Collection without tenant should return public resource ID"""
        body_data = {"id": "test-collection"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = _extract_collection_resource_id_from_post_body(
            cast(Request, request)
        )
        assert resource_id == "stac:collection:public:*"

    def test_collection_with_tenant_in_properties(self):
        """Collection with tenant in properties should extract it"""
        body_data = {
            "id": "test-collection",
            "properties": {"eic:tenant": "faketenant2"},
        }
        cached_body = json.dumps(body_data).encode()
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = _extract_collection_resource_id_from_post_body(
            cast(Request, request)
        )
        assert resource_id == "stac:collection:faketenant2:*"

    def test_no_cached_body_returns_none(self):
        """Missing cached body should return None"""
        request = MockRequest("/collections", method="POST")

        resource_id = _extract_collection_resource_id_from_post_body(
            cast(Request, request)
        )
        assert resource_id is None

    def test_invalid_json_returns_none(self):
        """Invalid JSON in cached body should return None"""
        cached_body = b"not valid json"
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = _extract_collection_resource_id_from_post_body(
            cast(Request, request)
        )
        assert resource_id is None


class TestExtractStacResourceId:
    """Test STAC API resource ID extraction"""

    def test_collection_get_with_tenant_in_url(self):
        """GET collection with tenant in URL should return tenant-specific resource ID"""
        request = MockRequest(
            "/api/stac/faketenant1/collections/test-collection",
            method="GET",
            tenant="faketenant1",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant1:*"

    def test_collection_get_without_tenant(self):
        """GET collection without tenant should return public resource ID"""
        request = MockRequest("/collections/test-collection", method="GET")

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:public:*"

    def test_collection_put_with_tenant_in_body(self):
        """PUT collection should extract tenant from body"""
        body_data = {"id": "test-collection", "eic:tenant": "faketenant1"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest(
            "/collections/test-collection",
            method="PUT",
            cached_body=cached_body,
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant1:*"

    def test_collection_patch_with_tenant_in_body(self):
        """PATCH collection should extract tenant from body"""
        body_data = {"id": "test-collection", "eic:tenant": "faketenant2"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest(
            "/collections/test-collection",
            method="PATCH",
            cached_body=cached_body,
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant2:*"

    def test_collection_put_without_tenant_in_body(self):
        """PUT collection without tenant in body should return public resource ID"""
        body_data = {"id": "test-collection"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest(
            "/collections/test-collection",
            method="PUT",
            cached_body=cached_body,
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:public:*"

    def test_item_get_with_tenant_in_url(self):
        """GET item with tenant in URL should return tenant-specific resource ID"""
        request = MockRequest(
            "/api/stac/faketenant1/collections/test-collection/items/test-item",
            method="GET",
            tenant="faketenant1",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:item:faketenant1:*"

    def test_item_get_without_tenant(self):
        """GET item without tenant should return public resource ID"""
        request = MockRequest(
            "/collections/test-collection/items/test-item",
            method="GET",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:item:public:*"

    def test_collection_items_endpoint_with_tenant(self):
        """Collection items endpoint with tenant should return collection pattern"""
        request = MockRequest(
            "/api/stac/faketenant1/collections/test-collection/items",
            method="GET",
            tenant="faketenant1",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant1:*"

    def test_collection_items_endpoint_without_tenant(self):
        """Collection items endpoint without tenant should return public pattern"""
        request = MockRequest(
            "/collections/test-collection/items",
            method="GET",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:public:*"

    def test_bulk_items_endpoint_with_tenant(self):
        """Bulk items endpoint with tenant should return collection pattern"""
        request = MockRequest(
            "/api/stac/faketenant1/collections/test-collection/bulk_items",
            method="POST",
            tenant="faketenant1",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant1:*"

    def test_bulk_items_endpoint_without_tenant(self):
        """Bulk items endpoint without tenant should return public pattern"""
        request = MockRequest(
            "/collections/test-collection/bulk_items",
            method="POST",
        )

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:public:*"

    def test_queryables_endpoint_returns_none(self):
        """Queryables endpoint should return None (no specific resource)"""
        request = MockRequest("/collections/test-collection/queryables", method="GET")

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id is None

    def test_search_endpoint_returns_none(self):
        """Search endpoint should return None (no specific resource)"""
        request = MockRequest("/search", method="POST")

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id is None

    def test_unknown_path_returns_none(self):
        """Unknown path should return None"""
        request = MockRequest("/unknown/path", method="GET")

        resource_id = extract_stac_resource_id(cast(Request, request))
        assert resource_id is None


class TestExtractIngestResourceId:
    """Test Ingest API resource ID extraction"""

    def test_post_collections_with_tenant_in_body(self):
        """POST /collections with tenant in body should return tenant-specific resource ID"""
        body_data = {"id": "test-collection", "eic:tenant": "faketenant1"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:faketenant1:*"

    def test_post_collections_without_tenant(self):
        """POST /collections without tenant should return public resource ID"""
        body_data = {"id": "test-collection"}
        cached_body = json.dumps(body_data).encode()
        request = MockRequest("/collections", method="POST", cached_body=cached_body)

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id == "stac:collection:public:*"

    def test_delete_collection_returns_collection_id(self):
        """DELETE /collections/{id} should return collection-specific resource ID"""
        request = MockRequest("/collections/test-collection", method="DELETE")

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id == "collection:test-collection"

    def test_get_collection_returns_collection_id(self):
        """GET /collections/{id} should return collection-specific resource ID"""
        request = MockRequest("/collections/test-collection", method="GET")

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id == "collection:test-collection"

    def test_post_items_returns_wildcard(self):
        """POST /items should return item wildcard"""
        request = MockRequest("/items", method="POST")

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id == "item:*"

    def test_ingestion_endpoints_return_none(self):
        """Ingestion endpoints are not protected resources and should return None"""
        # GET /ingestions/{id}
        request = MockRequest("/ingestions/test-ingestion", method="GET")
        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None

        # POST /ingestions
        request = MockRequest("/ingestions", method="POST")
        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None

        # PATCH /ingestions/{id}
        request = MockRequest("/ingestions/test-ingestion", method="PATCH")
        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None

        # DELETE /ingestions/{id}
        request = MockRequest("/ingestions/test-ingestion", method="DELETE")
        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None

    def test_unknown_path_returns_none(self):
        """Unknown path should return None"""
        request = MockRequest("/unknown/path", method="GET")

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None

    def test_post_collections_no_cached_body_returns_none(self):
        """POST /collections without cached body should return None"""
        request = MockRequest("/collections", method="POST")

        resource_id = extract_ingest_resource_id(cast(Request, request))
        assert resource_id is None
