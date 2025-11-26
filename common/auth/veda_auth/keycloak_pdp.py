"""Keycloak Policy Decision Point (PDP) Client

This provides a client for interacting with Keycloak's Authorization Services
to make authorization decisions via UMA (User-Managed Access) protocol.
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class KeycloakPDPClient:
    """Client for Keycloak Policy Decision Point (Authorization Services)

    This client calls Keycloak's UMA endpoints to get authorization decisions.
    """

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: Optional[str] = None,
        timeout: float = 5.0,
    ):
        """
        Args:
            keycloak_url: Base URL of Keycloak
            realm: Realm name
            client_id: Client ID for the resource server
            client_secret: Optional client secret for confidential clients
            timeout: Request timeout in seconds
        """
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

        self.token_endpoint = (
            f"{self.keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        )
        self.uma2_config_endpoint = (
            f"{self.keycloak_url}/realms/{realm}/.well-known/uma2-configuration"
        )

        self._client = httpx.AsyncClient(timeout=timeout)

    async def get_rpt(
        self,
        access_token: str,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Request the RPT (Requesting Party Token) from Keycloak
        Args:
            access_token: User's access token/Bearer token
            resources: List of resources being accessed
                Example: [
                    {
                        "resource_id": "stac:collection:tenant:my-collection",
                        "resource_scopes": ["create"]
                    }
                ]

        Returns:
            RPT token response. Keycloak returns permissions in the response JSON:
            {
                "access_token": "...",  # RPT JWT (contains permissions in authorization claim)
                "token_type": "Bearer",
                "permissions": [  # Permissions array (convenience field in response)
                    {
                        "rsid": "stac:collection:tenant:my-collection",  # Resource identifier (RPT format https://www.keycloak.org/docs/latest/authorization_services/#_service_obtaining_permissions)
                        # OR "resource_id": "..." (introspection format)
                        "scopes": ["create"]  # Granted scopes
                    }
                ]
            }
            https://www.keycloak.org/docs/latest/authorization_services/#_service_rpt_overview
        """
        permissions = []
        for resource in resources:
            resource_id = resource.get("resource_id")
            scopes = resource.get("resource_scopes", [])
            if resource_id and scopes:
                # Build permission string for UMA ticket request -> resource_id#scope1,scope2
                permission_str = f"{resource_id}#{','.join(scopes)}"
                permissions.append(permission_str)

        if not permissions:
            raise ValueError("At least one resource with scopes must be provided")

        # https://www.keycloak.org/docs/latest/authorization_services/#_service_authorization_api
        data_items = [
            ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
            ("audience", self.client_id),
        ]

        for permission in permissions:
            data_items.append(("permission", permission))

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if self.client_secret:
            data_items.append(("client_id", self.client_id))
            data_items.append(("client_secret", self.client_secret))

        try:
            response = await self._client.post(
                self.token_endpoint,
                data=data_items,  # type: ignore
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to get RPT from Keycloak: {e.response.status_code} {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"error getting RPT: {e}")
            raise

    def _extract_permissions_from_jwt(self, jwt_token: str) -> List[Dict[str, Any]]:
        """Extract permissions from RPT JWT token"""
        try:
            parts = jwt_token.split(".")
            if len(parts) != 3:
                logger.warning("Invalid JWT format")
                return []

            payload = parts[1]
            decoded_payload = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded_payload)

            authorization = claims.get("authorization", {})
            return authorization.get("permissions", [])

        except Exception as e:
            logger.warning(f"Failed to extract permissions from JWT: {e}")
            return []

    async def check_permission(
        self,
        access_token: str,
        resource_id: str,
        scope: str,
    ) -> bool:
        """Check if user has permission for a resource and scope

        Args:
            access_token: User's access token
            resource_id: Resource identifier
            scope: Scope/permission to check

        Returns:
            True if permission granted, False otherwise
        """
        try:
            rpt_response = await self.get_rpt(
                access_token=access_token,
                resources=[
                    {
                        "resource_id": resource_id,
                        "resource_scopes": [scope],
                    }
                ],
            )

            permissions = rpt_response.get("permissions", [])
            if not permissions:
                rpt_jwt = rpt_response.get("access_token")
                if rpt_jwt:
                    permissions = self._extract_permissions_from_jwt(rpt_jwt)
                    logger.debug(
                        f"Extracted {len(permissions)} permissions from RPT JWT"
                    )

            # https://www.keycloak.org/docs/latest/authorization_services/#_service_rpt_overview
            for permission in permissions:
                # Check rsid (RPT token format), resource_id (introspection format), or rsname (resource name)
                resource_identifier = (
                    permission.get("rsid")
                    or permission.get("resource_id")
                    or permission.get("rsname")
                )
                if resource_identifier == resource_id:
                    scopes = permission.get("scopes", [])
                    if scope in scopes:
                        return True

            return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                return False
            logger.error(
                f"Permission check failed: {e.response.status_code} {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking permission: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()
