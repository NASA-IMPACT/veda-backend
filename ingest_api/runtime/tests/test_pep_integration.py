"""Integration tests for PEP middleware on Ingest API's POST /collections endpoint"""

import importlib
import os
import uuid
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from veda_auth.keycloak_client import PermissionDeniedError, ResourceNotFoundError

from fastapi.testclient import TestClient

VALID_COLLECTION_TEMPLATE = {
    "type": "Collection",
    "title": "Test Collection for PEP",
    "links": [],
    "description": "Integration test collection for PEP middleware",
    "extent": {
        "spatial": {"bbox": [[-180, -90, 180, 90]]},
        "temporal": {"interval": [["2020-01-01T00:00:00Z", None]]},
    },
    "license": "MIT",
    "stac_version": "1.0.0",
    "stac_extensions": [],
}

COLLECTIONS_ENDPOINT = "/collections"

MOCK_KEYCLOAK_SECRET = {
    "id": "test-uma-client",
    "secret": "test-uma-secret",
}


@pytest.fixture(autouse=True)
def pep_environ(test_environ):
    """Set UMA env vars"""
    os.environ[
        "KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME"
    ] = "test/keycloak-uma-secret"
    yield
    os.environ.pop("KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME", None)


@pytest.fixture
def mock_pdp_client():
    """A mock PDP client with mocked check_permission function"""
    client = MagicMock()
    client.check_permission = MagicMock(return_value=True)
    return client


@pytest.fixture
def pep_app(mock_pdp_client, mock_ssm_parameter_store):
    """Reload the Ingest app with PEP middleware enabled and mocked dependencies"""
    import src.auth
    import src.config
    import src.main

    # reload to re-read the environment
    importlib.reload(src.config)
    importlib.reload(src.auth)

    with patch(
        "src.utils.get_keycloak_client_credentials",
        return_value=MOCK_KEYCLOAK_SECRET,
    ), patch(
        "veda_auth.keycloak_client.KeycloakPDPClient",
        return_value=mock_pdp_client,
    ), patch(
        "src.collection_publisher.CollectionPublisher.ingest",
    ):
        # reload now that we've patched the mocked dependencies
        importlib.reload(src.main)
        app = src.main.app
        yield app

    # restore original module state
    importlib.reload(src.config)
    importlib.reload(src.auth)
    importlib.reload(src.main)


@pytest.fixture
def pep_client(pep_app):
    """TestClient wrapping the PEP enabled Ingest app"""
    return TestClient(pep_app)


def _collection(tenant: Optional[str] = None) -> dict:
    """Builds a valid collection body"""
    body = dict(VALID_COLLECTION_TEMPLATE)
    body["id"] = f"pep-test-{uuid.uuid4().hex[:8]}"
    if tenant:
        body["eic:tenant"] = tenant
    return body


class TestIngestPEPIntegration:
    """Integration tests for PEP middleware on Ingest API POST /collections endpoint"""

    def test_post_collection_no_token_returns_401(self, pep_client):
        """POST /collections without Authorization header should return 401."""
        response = pep_client.post(COLLECTIONS_ENDPOINT, json=_collection())
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"

    def test_post_collection_authorized_succeeds(self, pep_client, mock_pdp_client):
        """POST /collections with valid Bearer and PDP allows should succeed"""
        mock_pdp_client.check_permission.return_value = True

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 201

        mock_pdp_client.check_permission.assert_called_once()
        call_kwargs = mock_pdp_client.check_permission.call_args
        assert (call_kwargs.kwargs.get("access_token")) == "fake-valid-token"
        assert (call_kwargs.kwargs.get("scope")) == "create"

    def test_post_collection_denied_returns_403(self, pep_client, mock_pdp_client):
        """POST /collections with valid Bearer where PDP denies should return 403"""
        mock_pdp_client.check_permission.side_effect = PermissionDeniedError(
            resource_id="stac:collection:test", scope="create"
        )

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 403
        assert "do not have permission" in response.json()["detail"]

    def test_post_collection_pdp_error_returns_502(self, pep_client, mock_pdp_client):
        """POST /collections where PDP raises an exception should return 502"""
        mock_pdp_client.check_permission.side_effect = Exception("Keycloak unavailable")

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 502
        assert "Authorization service" in response.json()["detail"]

    def test_post_collection_with_tenant_uses_tenant_resource(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with eic:tenant in body should check the tenant resource ID"""
        mock_pdp_client.check_permission.return_value = True

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(tenant="veda"),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 201

        call_kwargs = mock_pdp_client.check_permission.call_args
        resource_id = call_kwargs.kwargs.get("resource_id")
        assert resource_id == "stac:collection:veda:*"

    def test_post_collection_without_tenant_uses_public_resource(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections without eic:tenant should check the public resource ID"""
        mock_pdp_client.check_permission.return_value = True

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 201

        call_kwargs = mock_pdp_client.check_permission.call_args
        resource_id = call_kwargs.kwargs.get("resource_id")
        assert resource_id == "stac:collection:public:*"

    def test_post_collection_nonexistent_tenant_returns_404(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with a tenant that doesn't exist in Keycloak should return 404"""
        mock_pdp_client.check_permission.side_effect = ResourceNotFoundError(
            resource_id="stac:collection:nonexistent-tenant:*"
        )

        response = pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(tenant="nonexistent-tenant"),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]
        assert "nonexistent-tenant" in response.json()["detail"]
