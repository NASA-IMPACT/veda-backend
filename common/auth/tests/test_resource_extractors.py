"""Tests for resource extractors"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from veda_auth.resource_extractors import (
    STAC_COLLECTION_PUBLIC,
    STAC_COLLECTION_TEMPLATE,
    STAC_ITEM_PUBLIC,
    STAC_ITEM_TEMPLATE,
    _extract_collection_resource_id_from_post_body,
    _extract_tenant_from_body,
    extract_ingest_resource_id,
    extract_stac_resource_id,
)

from fastapi import HTTPException, Request


class TestExtractTenantFromBody:
    """Tests for _extract_tenant_from_body function"""

    def test_extract_tenant(self):
        """Test extracting tenant from body"""
        body_data = {"eic:tenant": "test-tenant", "id": "test-collection"}
        result = _extract_tenant_from_body(body_data)
        assert result == "test-tenant"

    def test_extract_tenant_custom_field(self):
        """Test extracting tenant with custom field name"""
        body_data = {"custom_tenant_field": "test-tenant"}
        result = _extract_tenant_from_body(
            body_data, tenant_field="custom_tenant_field"
        )
        assert result == "test-tenant"

    def test_no_tenant_in_body(self):
        """Test when tenant is not present in body"""
        body_data = {"id": "test-collection", "type": "Collection"}
        result = _extract_tenant_from_body(body_data)
        assert result is None

    def test_empty_body(self):
        """Test with empty body"""
        body_data = {}
        result = _extract_tenant_from_body(body_data)
        assert result is None


class TestExtractCollectionResourceIdFromPostBody:
    """Tests for _extract_collection_resource_id_from_post_body function"""

    @pytest.mark.asyncio
    async def test_extract_with_tenant(self):
        """Test extracting resource ID when tenant is present in body"""
        body_data = {"eic:tenant": "test-tenant", "id": "test-collection"}
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=test_body)

        result = await _extract_collection_resource_id_from_post_body(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_extract_without_tenant(self):
        """Test extracting resource ID when tenant is not present (defaults to public)."""
        body_data = {"id": "test-collection", "type": "Collection"}
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=test_body)

        result = await _extract_collection_resource_id_from_post_body(request)
        assert result == STAC_COLLECTION_PUBLIC

    @pytest.mark.asyncio
    async def test_extract_with_empty_body(self):
        """Test extracting resource ID with empty body raises HTTPException 400"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"")

        with pytest.raises(HTTPException) as exc_info:
            await _extract_collection_resource_id_from_post_body(request)
        assert exc_info.value.status_code == 400
        assert "empty body" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_extract_with_invalid_json(self):
        """Test extracting resource ID with invalid JSON, also returns None"""
        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"invalid json")

        result = await _extract_collection_resource_id_from_post_body(request)
        assert result is None


class TestExtractStacResourceId:
    """Tests for extract_stac_resource_id function"""

    @pytest.mark.asyncio
    async def test_get_collection_with_tenant(self):
        """Test extracting resource ID for GET collection with tenant"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "GET"
        request.state.tenant = "test-tenant"

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_get_collection_without_tenant(self):
        """Test extracting resource ID for GET collection without tenant (defaults to public)"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "GET"
        request.state = MagicMock()
        delattr(request.state, "tenant")

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_PUBLIC

    @pytest.mark.asyncio
    async def test_put_collection_with_tenant_in_body(self):
        """Test extracting resource ID for PUT collection with tenant in body"""
        body_data = {"eic:tenant": "test-tenant", "id": "test-collection"}
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "PUT"
        request.body = AsyncMock(return_value=test_body)

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_post_collections_create_with_tenant_in_body(self):
        """Test extracting resource ID for STAC POST /collections (create, from transactions enabled) with tenant in body"""
        body_data = {"eic:tenant": "test-tenant", "id": "new-collection"}
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.url.path = "/collections"
        request.method = "POST"
        request.body = AsyncMock(return_value=test_body)

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_post_collections_create_without_tenant_in_body(self):
        """Test extracting resource ID for STAC POST /collections (create, from transactions enabled) without tenant (defaults to public)"""
        body_data = {"id": "new-collection", "type": "Collection"}
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.url.path = "/collections"
        request.method = "POST"
        request.body = AsyncMock(return_value=test_body)

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_PUBLIC

    @pytest.mark.asyncio
    async def test_get_item_with_tenant(self):
        """Test extracting resource ID for GET item with tenant"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection/items/test-item"
        request.method = "GET"
        request.state.tenant = "test-tenant"

        result = await extract_stac_resource_id(request)
        assert result == STAC_ITEM_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_get_item_without_tenant_uses_public(self):
        """Test extracting resource ID for GET item without tenant (defaults to public)"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection/items/test-item"
        request.method = "GET"
        request.state = MagicMock()

        result = await extract_stac_resource_id(request)
        assert result == STAC_ITEM_TEMPLATE.format("public")

    @pytest.mark.asyncio
    async def test_post_items_with_tenant(self):
        """Test extracting resource ID for POST items with tenant"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection/items"
        request.method = "POST"
        request.state.tenant = "test-tenant"

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_post_bulk_items_with_tenant(self):
        """Test extracting resource ID for POST bulk_items with tenant"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection/bulk_items"
        request.method = "POST"
        request.state.tenant = "test-tenant"

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    @pytest.mark.asyncio
    async def test_item_paths_use_collection_tenant_resolver_when_available(self):
        """Item endpoints should use collection_tenant_resolver when configured on app state"""
        resolver = AsyncMock(return_value="resolver-tenant")

        def _build_request(path: str, method: str) -> Request:
            request = MagicMock(spec=Request)
            request.url.path = path
            request.method = method
            request.state = MagicMock()
            app = MagicMock()
            app.state.collection_tenant_resolver = resolver
            request.app = app
            return request

        item_request = _build_request(
            "/collections/test-collection/items/test-item", "GET"
        )
        item_result = await extract_stac_resource_id(item_request)
        assert item_result == STAC_ITEM_TEMPLATE.format("resolver-tenant")

        items_request = _build_request("/collections/test-collection/items", "POST")
        items_result = await extract_stac_resource_id(items_request)
        assert items_result == STAC_ITEM_TEMPLATE.format("resolver-tenant")

    @pytest.mark.asyncio
    async def test_collection_tenant_resolver_failure_falls_back_to_public(self):
        """When collection_tenant_resolver fails, item requests fall back to public"""
        resolver = AsyncMock(side_effect=Exception("resolver failed"))

        def _build_request(path: str, method: str) -> Request:
            request = MagicMock(spec=Request)
            request.url.path = path
            request.method = method
            request.state = MagicMock()
            app = MagicMock()
            app.state.collection_tenant_resolver = resolver
            request.app = app
            return request

        item_request = _build_request(
            "/collections/test-collection/items/test-item", "GET"
        )
        item_result = await extract_stac_resource_id(item_request)
        assert item_result == STAC_ITEM_PUBLIC

        items_request = _build_request("/collections/test-collection/items", "POST")
        items_result = await extract_stac_resource_id(items_request)
        assert items_result == STAC_COLLECTION_PUBLIC

        delete_collection_request = _build_request(
            "/collections/test-collection", "DELETE"
        )
        delete_collection_result = await extract_stac_resource_id(
            delete_collection_request
        )
        assert delete_collection_result == STAC_COLLECTION_PUBLIC

    @pytest.mark.asyncio
    async def test_delete_collection_uses_collection_tenant_resolver_when_available(
        self,
    ):
        """DELETE /collections/{id} should use collection_tenant_resolver"""
        resolver = AsyncMock(return_value="some-tenant")
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "DELETE"
        request.state = MagicMock()
        app = MagicMock()
        app.state.collection_tenant_resolver = resolver
        request.app = app

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("some-tenant")
        resolver.assert_awaited_once_with(request, "test-collection")

    @pytest.mark.asyncio
    async def test_delete_collection_resolver_none_falls_back_to_url_tenant(self):
        """When resolver returns None, fall back to request.state.tenant if present"""
        resolver = AsyncMock(return_value=None)
        request = MagicMock(spec=Request)
        request.url.path = "/collections/my-col"
        request.method = "DELETE"
        request.state = SimpleNamespace(tenant="url-tenant")
        request.app = SimpleNamespace(
            state=SimpleNamespace(collection_tenant_resolver=resolver)
        )

        result = await extract_stac_resource_id(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("url-tenant")


class TestExtractIngestResourceId:
    """Test Ingest API resource ID extraction"""

    async def test_delete_collection_falls_back_to_url_tenant_without_resolver(self):
        """DELETE with no resolver uses request.state.tenant when tenant-prefixed path set it"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "DELETE"
        request.state.tenant = "test-tenant"
        request.app = SimpleNamespace(state=SimpleNamespace())

        resource_id = await extract_ingest_resource_id(request)
        assert resource_id == STAC_COLLECTION_TEMPLATE.format("test-tenant")

    async def test_delete_collection_without_resolver_or_url_tenant_is_public(self):
        """DELETE with no resolver and no state.tenant uses stac:collection:public:*"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/foo"
        request.method = "DELETE"
        request.state = SimpleNamespace()
        request.app = SimpleNamespace(state=SimpleNamespace())

        assert await extract_ingest_resource_id(request) == STAC_COLLECTION_PUBLIC

    async def test_delete_collection_resolver_none_falls_back_to_url_tenant(self):
        """When resolver returns None, use request.state.tenant if set (tenant-prefixed paths)"""
        resolver = AsyncMock(return_value=None)
        request = MagicMock(spec=Request)
        request.url.path = "/collections/my-col"
        request.method = "DELETE"
        request.state = SimpleNamespace(tenant="url-tenant")
        request.app = SimpleNamespace(
            state=SimpleNamespace(collection_tenant_resolver=resolver)
        )

        assert await extract_ingest_resource_id(
            request
        ) == STAC_COLLECTION_TEMPLATE.format("url-tenant")

    async def test_delete_collection_uses_resolver_tenant(self):
        """DELETE uses resolved tenant (from database lookup) for Keycloak resource ID"""
        resolver = AsyncMock(return_value="veda")
        request = MagicMock(spec=Request)
        request.url.path = "/collections/foo"
        request.method = "DELETE"
        request.state = SimpleNamespace()
        request.app = SimpleNamespace(
            state=SimpleNamespace(collection_tenant_resolver=resolver)
        )

        rid = await extract_ingest_resource_id(request)
        assert rid == STAC_COLLECTION_TEMPLATE.format("veda")
        resolver.assert_awaited_once_with(request, "foo")

    async def test_delete_collection_resolver_raises_falls_back_to_public(self):
        """Resolver failures fall back to _stac_collection_resource_id (public if no URL tenant)"""
        resolver = AsyncMock(side_effect=RuntimeError("db unavailable"))
        request = MagicMock(spec=Request)
        request.url.path = "/collections/foo"
        request.method = "DELETE"
        request.state = SimpleNamespace()
        request.app = SimpleNamespace(
            state=SimpleNamespace(collection_tenant_resolver=resolver)
        )

        assert await extract_ingest_resource_id(request) == STAC_COLLECTION_PUBLIC

    async def test_delete_collection_magicmock_state_resolver_still_works(self):
        """Resolver runs even when request.state is a MagicMock (no real tenant)."""
        resolver = AsyncMock(return_value="tenant-a")
        request = MagicMock(spec=Request)
        request.url.path = "/collections/bar"
        request.method = "DELETE"
        request.state = MagicMock()
        request.app = SimpleNamespace(
            state=SimpleNamespace(collection_tenant_resolver=resolver)
        )

        assert await extract_ingest_resource_id(
            request
        ) == STAC_COLLECTION_TEMPLATE.format("tenant-a")
        resolver.assert_awaited_once_with(request, "bar")
