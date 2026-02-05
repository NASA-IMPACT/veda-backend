"""Tests for resource extractors"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from veda_auth.resource_extractors import (
    STAC_COLLECTION_PUBLIC,
    STAC_COLLECTION_TEMPLATE,
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

    @pytest.mark.asyncio
    async def test_extract_tenant_from_properties(self):
        """Test extracting resource ID when tenant is in properties"""
        body_data = {
            "id": "test-collection",
            "properties": {"eic:tenant": "test-tenant"},
        }
        test_body = json.dumps(body_data).encode("utf-8")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=test_body)

        result = await _extract_collection_resource_id_from_post_body(request)
        assert result == STAC_COLLECTION_TEMPLATE.format("test-tenant")


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
    async def test_get_item_with_tenant(self):
        """Test extracting resource ID for GET item with tenant"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection/items/test-item"
        request.method = "GET"
        request.state.tenant = "test-tenant"

        result = await extract_stac_resource_id(request)
        assert result == STAC_ITEM_TEMPLATE.format("test-tenant")

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


class TestExtractIngestResourceId:
    """Test Ingest API resource ID extraction"""

    async def test_delete_collection_returns_collection_id(self):
        """DELETE /collections/{id} should return collection-specific resource ID"""
        request = MagicMock(spec=Request)
        request.url.path = "/collections/test-collection"
        request.method = "DELETE"
        request.state.tenant = "test-tenant"

        resource_id = await extract_ingest_resource_id(request)
        assert resource_id == "collection:test-collection"
