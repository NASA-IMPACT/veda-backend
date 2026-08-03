"""Unit tests for TenantExtractionMiddleware"""

from typing import Any

from fastapi import FastAPI, Request
from src.tenant_extraction_middleware import TenantExtractionMiddleware
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send


def _inject_root_path(app: ASGIApp, root_path: str) -> ASGIApp:
    """Add root_path to each HTTP scope."""

    async def asgi(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            scope = {**scope, "root_path": root_path}
        await app(scope, receive, send)

    return asgi


def _request_after_middleware(request: Request) -> dict[str, Any]:
    """Used for JSON assertions"""
    return {
        "scope_path": request.scope["path"],
        "root_path": request.scope.get("root_path", ""),
        "tenant": getattr(request.state, "tenant", None),
    }


def _stac_client_with_root_path(root_path: str) -> TestClient:
    """Client with middleware"""
    app = FastAPI()
    app.add_middleware(TenantExtractionMiddleware)

    @app.get("/")
    async def stac_root(request: Request):
        return _request_after_middleware(request)

    @app.get("/collections")
    async def stac_collections(request: Request):
        return _request_after_middleware(request)

    wrapped = _inject_root_path(app, root_path)
    return TestClient(wrapped)


def test_preserves_trailing_slash_on_stac_root():
    """Keep root_path/ unchanged"""
    client = _stac_client_with_root_path("/api/stac")
    response = client.get("/api/stac/")
    assert response.status_code == 200
    data = response.json()
    assert data["scope_path"] == "/api/stac/"
    assert data["root_path"] == "/api/stac"
    assert data["tenant"] is None


def test_strips_trailing_slash_on_nested_path():
    """Normalize trailing slash on non-root paths under root_path"""
    client = _stac_client_with_root_path("/api/stac")
    response = client.get("/api/stac/collections/")
    assert response.status_code == 200
    data = response.json()
    assert data["scope_path"] == "/api/stac/collections"
    assert data["tenant"] is None


def test_strips_trailing_slash_when_root_path_empty():
    """First path segment must be a standard endpoint so no tenant is extracted"""
    app = FastAPI()
    app.add_middleware(TenantExtractionMiddleware)

    @app.get("/collections/items")
    async def items(request: Request):
        return _request_after_middleware(request)

    client = TestClient(app)
    response = client.get("/collections/items/")
    assert response.status_code == 200
    data = response.json()
    assert data["scope_path"] == "/collections/items"
    assert data["root_path"] == ""
    assert data["tenant"] is None


def test_extracts_tenant_and_rewrites_path_for_tenant_collections():
    """Strip tenant segment from path and set request.state.tenant"""
    client = _stac_client_with_root_path("/api/stac")
    response = client.get("/api/stac/veda/collections/")
    assert response.status_code == 200
    data = response.json()
    assert data["scope_path"] == "/api/stac/collections"
    assert data["tenant"] == "veda"
