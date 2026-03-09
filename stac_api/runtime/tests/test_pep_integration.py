"""Integration tests for PEP middleware"""
import importlib
import os
import uuid
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
import src.app
import src.config
from httpx import ASGITransport, AsyncClient
from veda_auth.keycloak_client import PermissionDeniedError, ResourceNotFoundError

from stac_fastapi.pgstac.db import close_db_connection, connect_to_db

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
}

ROOT_PATH = "/api/stac"
COLLECTIONS_ENDPOINT = f"{ROOT_PATH}/collections"


MOCK_KEYCLOAK_SECRET = {
    "id": "test-uma-client",
    "secret": "test-uma-secret",
}


@pytest.fixture(autouse=True)
def pep_environ():
    """Set UMA and transaction env vars for PEP middleware tests"""
    os.environ[
        "VEDA_STAC_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME"
    ] = "test/keycloak-uma-secret"
    os.environ[
        "VEDA_STAC_OPENID_CONFIGURATION_URL"
    ] = "https://auth.example.com/realms/test-realm/.well-known/openid-configuration"
    os.environ["VEDA_STAC_ENABLE_TRANSACTIONS"] = "True"
    os.environ["VEDA_STAC_ENABLE_STAC_AUTH_PROXY"] = "True"
    os.environ["VEDA_STAC_ROOT_PATH"] = ROOT_PATH
    yield
    os.environ.pop("VEDA_STAC_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME", None)
    os.environ.pop("VEDA_STAC_ENABLE_TRANSACTIONS", None)
    os.environ.pop("VEDA_STAC_ENABLE_STAC_AUTH_PROXY", None)
    os.environ.pop("VEDA_STAC_ROOT_PATH", None)


@pytest.fixture
def mock_pdp_client():
    """A mock PDP client with mocked check_permission"""
    client = MagicMock()
    client.check_permission = MagicMock(return_value=True)
    return client


@pytest.fixture
async def pep_app(mock_pdp_client):
    """Load the STAC app with PEP and PDP client mocks"""

    # clear config cache and reload so we get root_path/transactions from pep_environ
    src.config.ApiSettings.cache_clear()
    importlib.reload(src.config)

    with patch("src.config.get_secret_dict", return_value=MOCK_KEYCLOAK_SECRET), patch(
        "veda_auth.keycloak_client.KeycloakPDPClient", return_value=mock_pdp_client
    ):
        # reload with mocked dependencies
        importlib.reload(src.app)
        app = src.app.app

        await connect_to_db(app, add_write_connection_pool=True)
        yield app
        await close_db_connection(app)

    # restore original module
    src.config.ApiSettings.cache_clear()
    importlib.reload(src.config)


@pytest.fixture
async def pep_client(pep_app):
    """PEP client for testing"""
    async with AsyncClient(
        transport=ASGITransport(app=pep_app), base_url="http://test"
    ) as client:
        yield client


def _collection(tenant: Optional[str] = None) -> dict:
    """Build a valid STAC collection"""
    body = dict(VALID_COLLECTION_TEMPLATE)
    body["id"] = f"pep-test-{uuid.uuid4().hex[:8]}"
    if tenant:
        body["eic:tenant"] = tenant
    return body


class TestPEPIntegration:
    """Integration tests for PEP middleware for POST /collections endpoint"""

    @pytest.mark.asyncio
    async def test_post_collection_no_token_returns_401(self, pep_client):
        """POST /collections without Authorization header should return 401"""
        response = await pep_client.post(COLLECTIONS_ENDPOINT, json=_collection())
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_post_collection_authorized_succeeds(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with valid Bearer"""
        mock_pdp_client.check_permission.return_value = True
        collection = _collection()

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=collection,
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        mock_pdp_client.check_permission.assert_called_once()
        call_kwargs = mock_pdp_client.check_permission.call_args

        assert response.status_code == 201
        assert call_kwargs.kwargs.get("access_token") == "fake-valid-token"
        assert call_kwargs.kwargs.get("scope") == "create"

        await pep_client.delete(
            f"{COLLECTIONS_ENDPOINT}/{collection['id']}",
            headers={"Authorization": "Bearer fake-valid-token"},
        )

    @pytest.mark.asyncio
    async def test_post_collection_denied_returns_403(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with valid Bearer where PDP denies with 403"""
        mock_pdp_client.check_permission.side_effect = PermissionDeniedError(
            resource_id="stac:collection:test", scope="create"
        )

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 403
        assert "do not have permission" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_post_collection_pdp_error_returns_502(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections where PDP raises 502"""
        mock_pdp_client.check_permission.side_effect = Exception("Keycloak Unavailable")

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 502
        assert "Authorization service" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_post_collection_with_tenant_uses_tenant_resource(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with tenant in body and PDP called with tenant resource ID"""
        mock_pdp_client.check_permission.return_value = True
        collection = _collection(tenant="veda")

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=collection,
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 201

        call_kwargs = mock_pdp_client.check_permission.call_args
        resource_id = call_kwargs.kwargs.get("resource_id")
        assert resource_id == "stac:collection:veda:*"

        await pep_client.delete(
            f"{COLLECTIONS_ENDPOINT}/{collection['id']}",
            headers={"Authorization": "Bearer fake-valid-token"},
        )

    @pytest.mark.asyncio
    async def test_post_collection_without_tenant_uses_public_resource(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections without tenant in body so PDP is called with public resource ID"""
        mock_pdp_client.check_permission.return_value = True
        collection = _collection()

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=collection,
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 201

        call_kwargs = mock_pdp_client.check_permission.call_args
        resource_id = call_kwargs.kwargs.get("resource_id")
        assert resource_id == "stac:collection:public:*"

        await pep_client.delete(
            f"{COLLECTIONS_ENDPOINT}/{collection['id']}",
            headers={"Authorization": "Bearer fake-valid-token"},
        )

    @pytest.mark.asyncio
    async def test_post_collection_nonexistent_tenant_returns_404(
        self, pep_client, mock_pdp_client
    ):
        """POST /collections with a tenant that doesn't exist in Keycloak should return 404"""
        mock_pdp_client.check_permission.side_effect = ResourceNotFoundError(
            resource_id="stac:collection:nonexistent-tenant:*"
        )

        response = await pep_client.post(
            COLLECTIONS_ENDPOINT,
            json=_collection(tenant="nonexistent-tenant"),
            headers={"Authorization": "Bearer fake-valid-token"},
        )
        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]
        assert "nonexistent-tenant" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_collections_not_affected_by_pep(self, pep_client):
        """GET /collections should not be intercepted by PEP (because its not a protected route)"""
        response = await pep_client.get(COLLECTIONS_ENDPOINT)
        assert response.status_code == 200
