"""Unit tests for PEP middleware route matching"""

from unittest.mock import MagicMock

import pytest
from veda_auth.pep_middleware import (
    DEFAULT_PROTECTED_ROUTES,
    INGEST_PROTECTED_ROUTES,
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
        """POST collections should return create and POST"""
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
        """PUT /collections/{id} does not match DEFAULT_PROTECTED_ROUTES so it returns None"""
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
        """GET on collections should return None"""
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
    """STAC_PROTECTED_ROUTES (all collection and item write operations)"""

    @pytest.fixture
    def middleware(self):
        """PEP Middlware mock"""
        app = MagicMock()
        return PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=STAC_PROTECTED_ROUTES,
        )

    def test_post_collections_matches_create(self, middleware):
        """POST /collections matches with scope create"""
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections", "POST")
        )
        assert result == ("create", "POST")

    def test_put_collection_matches_update(self, middleware):
        """PUT /collections/{id} matches with scope update"""
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection", "PUT")
        )
        assert result == ("update", "PUT")

    def test_patch_collection_matches_update(self, middleware):
        """PATCH /collections/{id} matches with scope update"""
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections/some-collection", "PATCH")
        )
        assert result == ("update", "PATCH")

    def test_get_collections_no_match(self, middleware):
        """GET /collections does not match so it returns None"""
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/collections", "GET")
        )
        assert result is None

    def test_search_no_match(self, middleware):
        """POST /search does not match so it returns None"""
        result = middleware._get_matching_scope_and_route(
            _request("/api/stac/search", "POST")
        )
        assert result is None


class TestIngestProtectedRoutes:
    """INGEST_PROTECTED_ROUTES (ingest collection POST and DELETE endpoints)"""

    @pytest.fixture
    def middleware(self):
        """PEP middleware mock for ingest endpoints"""
        app = MagicMock()
        return PEPMiddleware(
            app,
            pdp_client=MagicMock(),
            resource_extractor=MagicMock(),
            protected_routes=INGEST_PROTECTED_ROUTES,
        )

    def test_post_collections_matches_create(self, middleware):
        """POST /collections matches with scope create"""
        result = middleware._get_matching_scope_and_route(
            _request("/collections", "POST")
        )
        assert result == ("create", "POST")

    def test_delete_collection_matches_delete_scope(self, middleware):
        """DELETE /collections matches with scope delete"""
        result = middleware._get_matching_scope_and_route(
            _request("/collections/my-collection", "DELETE")
        )
        assert result == ("delete", "DELETE")
