"""Unit tests for PEP middleware route matching"""

from unittest.mock import MagicMock

import pytest

from veda_auth.pep_middleware import (
    DEFAULT_PROTECTED_ROUTES,
    STAC_PROTECTED_ROUTES,
    PEPMiddleware,
)


def _request(path: str, method: str = "GET"):
    """Request mock for route matching"""
    req = MagicMock()
    req.url.path = path.rstrip("/") or "/"
    req.method = method.upper()
    return req


class TestDefaultProtectedRoutes:
    """DEFAULT_PROTECTED_ROUTES tests"""

    def test_post_collections_matches(self):
        app = MagicMock()
        middleware = PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=DEFAULT_PROTECTED_ROUTES,
        )
        result = middleware._get_matching_scope_and_route(
            _request("/collections", "POST")
        )
        assert result == ("create", "POST")

    def test_put_collections_no_match(self):
        app = MagicMock()
        middleware = PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=DEFAULT_PROTECTED_ROUTES,
        )
        result = middleware._get_matching_scope_and_route(
            _request("/collections/random", "PUT")
        )
        assert result is None

    def test_get_collections_no_match(self):
        app = MagicMock()
        middleware = PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=DEFAULT_PROTECTED_ROUTES,
        )
        result = middleware._get_matching_scope_and_route(
            _request("/collections", "GET")
        )
        assert result is None


class TestStacProtectedRoutes:
    """STAC_PROTECTED_ROUTES  (all collection and item write operations)"""

    @pytest.fixture
    def middleware(self):
        app = MagicMock()
        return PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=STAC_PROTECTED_ROUTES,
        )

    def test_post_collections_matches_create(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections", "POST")
        )
        assert result == ("create", "POST")

    def test_put_collection_matches_update(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection", "PUT")
        )
        assert result == ("update", "PUT")

    def test_patch_collection_matches_update(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection", "PATCH")
        )
        assert result == ("update", "PATCH")

    def test_delete_collection_matches_delete(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection", "DELETE")
        )
        assert result == ("delete", "DELETE")

    def test_post_items_matches_create(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/items", "POST")
        )
        assert result == ("create", "POST")

    def test_put_item_matches_update(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/items/item-1", "PUT")
        )
        assert result == ("update", "PUT")

    def test_patch_item_matches_update(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/items/item-1", "PATCH")
        )
        assert result == ("update", "PATCH")

    def test_delete_item_matches_delete(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/items/item-1", "DELETE")
        )
        assert result == ("delete", "DELETE")

    def test_post_bulk_items_matches_create(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/bulk_items", "POST")
        )
        assert result == ("create", "POST")

    def test_get_collections_no_match(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections", "GET")
        )
        assert result is None

    def test_get_collection_items_no_match(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection/items", "GET")
        )
        assert result is None

    def test_search_no_match(self, middleware):
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/search", "POST")
        )
        assert result is None
