"""Tests for PEP Middleware"""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from veda_auth.keycloak_pdp import KeycloakPDPClient
from veda_auth.pep_middleware import PEPMiddleware

from fastapi import FastAPI, Request
from starlette.testclient import TestClient


@pytest.fixture
def mock_pdp_client():
    """Create a mock KeycloakPDPClient"""
    client = MagicMock(spec=KeycloakPDPClient)
    client.check_permission = AsyncMock(return_value=True)
    return client


@pytest.fixture
def basic_resource_extractor():
    """Basic resource extractor for testing"""

    def extractor(request: Request):
        if request.url.path == "/test-resource":
            return "test:resource:123"
        return None

    return extractor


@pytest.fixture
def test_app(mock_pdp_client, basic_resource_extractor):
    """Create a test FastAPI app with PEP middleware"""
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/test-resource")
    def get_resource():
        return {"resource": "data"}

    @app.post("/test-resource")
    async def create_resource(request: Request):
        body = await request.json()
        return {"created": body}

    @app.put("/test-resource")
    async def update_resource(request: Request):
        body = await request.json()
        return {"updated": body}

    @app.delete("/test-resource")
    def delete_resource():
        return {"deleted": True}

    @app.get("/public-endpoint")
    def public_endpoint():
        return {"public": True}

    app.add_middleware(
        PEPMiddleware,
        pdp_client=mock_pdp_client,
        resource_extractor=basic_resource_extractor,
        public_paths={"/health", "/public-endpoint"},
    )

    return app


@pytest.fixture
def client(test_app):
    """Create a test client"""
    return TestClient(test_app)


class TestPublicPaths:
    """Test that public paths bypass authentication and authorization"""

    def test_health_endpoint_bypasses_auth(self, client):
        """Health endpoint should not require authentication or authorization"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_custom_public_path_bypasses_auth(self, client):
        """Custom public paths should not require authentication or authorization"""
        response = client.get("/public-endpoint")
        assert response.status_code == 200
        assert response.json() == {"public": True}


class TestReadOperations:
    """Test that read operations bypass authorization"""

    def test_get_request_bypasses_auth(self, client, mock_pdp_client):
        """GET requests require no token or permission check"""
        response = client.get("/test-resource")
        assert response.status_code == 200
        # Verify PDP client was not called
        mock_pdp_client.check_permission.assert_not_called()


class TestWriteOperations:
    """Test write operations (POST, PUT, DELETE)"""

    def test_post_without_token_returns_401(self, client):
        """POST without token should return 401"""
        response = client.post("/test-resource", json={"data": "test"})
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_post_with_token_and_permission_returns_200(self, client, mock_pdp_client):
        """POST with valid token and permission should succeed"""
        mock_pdp_client.check_permission.return_value = True

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        mock_pdp_client.check_permission.assert_called_once_with(
            access_token="valid-token",
            resource_id="test:resource:123",
            scope="create",
        )

    def test_post_with_token_but_no_permission_returns_403(
        self, client, mock_pdp_client
    ):
        """POST with token but no permission should return 403"""
        mock_pdp_client.check_permission.return_value = False

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
        mock_pdp_client.check_permission.assert_called_once()

    def test_put_with_token_and_permission_returns_200(self, client, mock_pdp_client):
        """PUT with valid token and permission should succeed"""
        mock_pdp_client.check_permission.return_value = True

        response = client.put(
            "/test-resource",
            json={"data": "updated"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        mock_pdp_client.check_permission.assert_called_once_with(
            access_token="valid-token",
            resource_id="test:resource:123",
            scope="update",
        )

    # def test_delete_with_token_and_permission_returns_200(
    #     self, client, mock_pdp_client
    # ):
    #     """DELETE with valid token and permission should succeed"""
    #     mock_pdp_client.check_permission.return_value = True

    #     response = client.delete(
    #         "/test-resource",
    #         headers={"Authorization": "Bearer valid-token"},
    #     )
    #     assert response.status_code == 200
    #     mock_pdp_client.check_permission.assert_called_once_with(
    #         access_token="valid-token",
    #         resource_id="test:resource:123",
    #         scope="delete",
    #     )


class TestBodyCaching:
    """Test that request body is cached for POST/PUT"""

    def test_post_body_is_cached(self, client, mock_pdp_client):
        """POST request body should be cached in request.state"""
        body_data = {"id": "test-collection", "eic:tenant": "test-tenant"}

        # Create a custom resource extractor that checks for cached body
        def body_checking_extractor(request: Request):
            cached_body = getattr(request.state, "_cached_body", None)
            if cached_body:
                data = json.loads(cached_body)
                if data.get("id") == "test-collection":
                    return f"collection:{data['id']}"
            return None

        app = FastAPI()

        @app.post("/collections")
        async def create_collection(request: Request):
            # Verify body can still be read
            body = await request.json()
            return {"created": body}

        app.add_middleware(
            PEPMiddleware,
            pdp_client=mock_pdp_client,
            resource_extractor=body_checking_extractor,
        )

        test_client = TestClient(app)
        mock_pdp_client.check_permission.return_value = True
        response = test_client.post(
            "/collections",
            json=body_data,
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        assert response.json()["created"] == body_data

    def test_put_body_is_cached(self, client, mock_pdp_client):
        """PUT request body should be cached"""
        body_data = {"data": "updated"}

        response = client.put(
            "/test-resource",
            json=body_data,
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200


class TestResourceExtraction:
    """Test resource ID extraction"""

    def test_no_resource_id_for_write_returns_403(self, client):
        """Write operation with no extractable resource ID should return 403"""

        def no_resource_extractor(request: Request):
            return None

        app = FastAPI()

        @app.post("/unknown-path")
        def unknown():
            return {"ok": True}

        app.add_middleware(
            PEPMiddleware,
            pdp_client=MagicMock(spec=KeycloakPDPClient),
            resource_extractor=no_resource_extractor,
        )

        test_client = TestClient(app)
        response = test_client.post(
            "/unknown-path",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 403
        assert "Cannot determine resource" in response.json()["detail"]

    def test_no_resource_id_for_read_allowed(self, client):
        """Read operations on endpoints without specific resources should be allowed"""

        def no_resource_extractor(request: Request):
            return None

        app = FastAPI()

        @app.get("/search")
        def search():
            return {"ok": True}

        app.add_middleware(
            PEPMiddleware,
            pdp_client=MagicMock(spec=KeycloakPDPClient),
            resource_extractor=no_resource_extractor,
        )

        test_client = TestClient(app)
        response = test_client.get("/search")

        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling from Keycloak PDP"""

    def test_pdp_401_error_returns_401(self, client, mock_pdp_client):
        """PDP returning 401 should result in 401 response"""
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = "Invalid token"

        mock_pdp_client.check_permission.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=error_response,
        )

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired token"}
        assert "WWW-Authenticate" in response.headers

    def test_pdp_403_error_returns_403(self, client, mock_pdp_client):
        """PDP returning 403 should result in 403 response"""
        error_response = MagicMock()
        error_response.status_code = 403
        error_response.text = "Forbidden"

        mock_pdp_client.check_permission.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=error_response,
        )

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Insufficient permissions"}

    def test_pdp_500_error_returns_502(self, client, mock_pdp_client):
        """PDP returning 500 should result in 502 Bad Gateway"""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        mock_pdp_client.check_permission.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=error_response,
        )

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 502
        assert response.json() == {"detail": "Authorization service error"}

    def test_pdp_unexpected_error_returns_500(self, client, mock_pdp_client):
        """Unexpected errors from PDP should result in 500"""
        mock_pdp_client.check_permission.side_effect = Exception("Unexpected error")

        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Authorization service error"}


class TestScopeMapping:
    """Test HTTP method to scope mapping"""

    def test_post_maps_to_create_scope(self, client, mock_pdp_client):
        """POST should map to 'create' scope"""
        mock_pdp_client.check_permission.return_value = True

        client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        call_args = mock_pdp_client.check_permission.call_args
        assert call_args.kwargs["scope"] == "create"

    def test_put_maps_to_update_scope(self, client, mock_pdp_client):
        """PUT should map to 'update' scope"""
        mock_pdp_client.check_permission.return_value = True

        client.put(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        call_args = mock_pdp_client.check_permission.call_args
        assert call_args.kwargs["scope"] == "update"

    def test_patch_maps_to_update_scope(self, client, mock_pdp_client):
        """PATCH should map to 'update' scope"""
        # Add PATCH endpoint
        app = FastAPI()

        app.add_middleware(
            PEPMiddleware,
            pdp_client=mock_pdp_client,
            resource_extractor=lambda r: "test:resource:123",
        )

        test_client = TestClient(app)
        mock_pdp_client.check_permission.return_value = True

        test_client.patch(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer token"},
        )

        call_args = mock_pdp_client.check_permission.call_args
        assert call_args.kwargs["scope"] == "update"

    def test_delete_maps_to_delete_scope(self, client, mock_pdp_client):
        """DELETE should map to 'delete' scope"""
        mock_pdp_client.check_permission.return_value = True

        client.delete(
            "/test-resource",
            headers={"Authorization": "Bearer token"},
        )

        call_args = mock_pdp_client.check_permission.call_args
        assert call_args.kwargs["scope"] == "delete"


class TestTokenExtraction:
    """Test access token extraction from headers"""

    def test_bearer_token_extracted(self, client, mock_pdp_client):
        """Bearer token should be extracted from Authorization header"""
        mock_pdp_client.check_permission.return_value = True

        client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "Bearer my-token-123"},
        )

        call_args = mock_pdp_client.check_permission.call_args
        assert call_args.kwargs["access_token"] == "my-token-123"

    def test_token_without_bearer_prefix_fails(self, client):
        """Token without 'Bearer ' prefix should be treated as missing"""
        response = client.post(
            "/test-resource",
            json={"data": "test"},
            headers={"Authorization": "my-token-123"},  # Missing "Bearer "
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required"}


class TestPublicPathMatching:
    """Test public path matching logic"""

    def test_exact_path_match(self, client):
        """Exact path match should bypass auth"""
        response = client.get("/health")
        assert response.status_code == 200
