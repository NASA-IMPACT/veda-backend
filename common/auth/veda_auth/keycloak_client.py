"""Keycloak Policy Decision Point (PDP) Client

This provides a client for interacting with Keycloak's Authorization Services
to make authorization decisions via UMA (User-Managed Access) protocol.
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


def _add_base64_padding(payload: str) -> str:
    """Add padding to base64 string if needed

    JWT tokens use URL-safe base64 encoding (Base64URL) which omits padding
    characters (`=`) to avoid issues in URLs and HTTP headers.

    Python's base64.urlsafe_b64decode() requires proper padding (length must be
    a multiple of 4) or it raises binascii.Error: Incorrect padding.
    """
    # determine the padding needed to make length a multiple of 4
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    return payload


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

        self._timeout = timeout

    def get_rpt(
        self,
        access_token: str,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Request the RPT (Requesting Party Token) from Keycloak"""
        permissions = []
        for resource in resources:
            resource_id = resource.get("resource_id")
            scopes = resource.get("resource_scopes", [])
            if resource_id and scopes:
                permission_str = f"{resource_id}#{','.join(scopes)}"
                permissions.append(permission_str)

        # https://www.keycloak.org/docs/latest/authorization_services/#_service_authorization_api
        data_dict: Dict[str, Any] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "audience": self.client_id,
        }

        permission_list = permissions

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if self.client_secret:
            data_dict["client_id"] = self.client_id
            data_dict["client_secret"] = self.client_secret

        try:
            form_data = [
                ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
                ("audience", str(self.client_id)),
            ]
            for permission in permission_list:
                form_data.append(("permission", str(permission)))
            if self.client_secret:
                form_data.append(("client_id", str(self.client_id)))
                form_data.append(("client_secret", str(self.client_secret)))

            form_data_encoded = urlencode(form_data, doseq=True)

            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self.token_endpoint,
                    content=form_data_encoded.encode("utf-8"),
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
                logger.warning(
                    f"Invalid JWT format: expected 3 parts, got {len(parts)}"
                )
                return []

            payload = parts[1]
            payload = _add_base64_padding(payload)
            decoded_payload = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded_payload)

            authorization = claims.get("authorization", {})
            permissions = authorization.get("permissions", [])
            logger.info(
                f"Extracted {len(permissions)} permissions from JWT authorization claim"
            )
            if permissions:
                logger.debug(f"Sample permission: {permissions[0]}")
            return permissions

        except Exception as e:
            logger.warning(f"Failed to extract permissions from JWT: {e}")
            return []

    def check_permission(
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
            rpt_response = self.get_rpt(
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

    def _decode_jwt_payload(self, token: str) -> Dict[str, Any]:
        """Decode JWT payload to extract the claims"""
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT token")

        payload = parts[1]
        payload = _add_base64_padding(payload)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    def _extract_tenants_from_token(self, access_token: str) -> List[str]:
        """Extract tenant names from user token claims"""
        try:
            claims = self._decode_jwt_payload(access_token)
            tenants = []

            # Check group_membership
            group_membership = claims.get("group_membership", {})
            if isinstance(group_membership, dict):
                tenant_groups = group_membership.get("tenants", [])
                for group in tenant_groups:
                    if "/Tenants/" in group:
                        parts = group.split("/")
                        if len(parts) >= 3:
                            tenants.append(parts[2])

            # Check groups array
            groups = claims.get("groups", [])
            for group in groups:
                if isinstance(group, str) and "/Tenants/" in group:
                    parts = group.split("/")
                    if len(parts) >= 3:
                        tenants.append(parts[2])

            return list(set(tenants))  # remove duplicates
        except Exception as e:
            logger.warning(f"Could not extract tenants from token: {e}")
            return []

    def get_tenants_with_create_update_access(
        self,
        access_token: str,
        tenant_list: Optional[List[str]] = None,
        resource_type: str = "collection",
    ) -> List[str]:
        """Get list of tenants the user has create and update access to"""

        # extract tenants from token
        if tenant_list is None:
            tenant_list = self._extract_tenants_from_token(access_token)
            if "public" not in tenant_list:
                tenant_list.append("public")

        try:
            rpt_response = self.get_rpt(
                access_token=access_token,
                resources=[],  # empty resources so it get all permissions
            )

            permissions = rpt_response.get("permissions", [])
            logger.info(f"Got {len(permissions)} permissions from RPT response JSON")

            if not permissions:
                rpt_jwt = rpt_response.get("access_token")
                if rpt_jwt:
                    logger.info(
                        "No permissions in response JSON, extracting from JWT token"
                    )
                    permissions = self._extract_permissions_from_jwt(rpt_jwt)
                    logger.info(
                        f"Extracted {len(permissions)} permissions from RPT JWT"
                    )
                    if permissions:
                        logger.debug(
                            f"Sample permission from JWT: {permissions[0] if permissions else 'None'}"
                        )
                else:
                    logger.warning(
                        "No permissions in RPT response and no access_token JWT"
                    )

            if not permissions:
                logger.warning("No permissions found in RPT response")
                return []

            logger.info(
                f"Processing {len(permissions)} permissions for resource_type={resource_type}"
            )

            # Extract tenants that have both create and update scopes
            tenant_scopes: Dict[str, set] = {}

            for permission in permissions:
                # Get resource identifier - use rsname (resource name) or resource_id
                # rsname contains the actual resource name like "stac:collection:tenant:*"
                resource_identifier = permission.get("rsname") or permission.get(
                    "resource_id"
                )

                if not resource_identifier:
                    logger.info(f"Permission missing resource identifier: {permission}")
                    continue

                logger.info(
                    f"Processing permission: resource_identifier={resource_identifier}, scopes={permission.get('scopes', [])}"
                )

                # Parse resource name: "stac:collection:tenant:*" or "stac:item:tenant:*"
                # Skip if it's a UUID (doesn't contain colons in the expected format)
                if ":" not in resource_identifier:
                    logger.info(
                        f"Skipping UUID resource identifier (not a resource name): {resource_identifier}"
                    )
                    continue

                parts = resource_identifier.split(":")
                logger.info(f"Split resource_identifier into parts: {parts}")

                if len(parts) >= 3:
                    resource_category = parts[1]  # "collection" or "item"
                    tenant = parts[2]
                    scopes = set(permission.get("scopes", []))

                    logger.info(
                        f"Resource: category={resource_category}, tenant={tenant}, scopes={scopes} {resource_type}"
                    )

                    if resource_category == resource_type:
                        if tenant not in tenant_scopes:
                            tenant_scopes[tenant] = set()

                        tenant_scopes[tenant].update(scopes)
                        logger.info(
                            f"Found tenant {tenant} with scopes {scopes} for {resource_type}"
                        )
                    else:
                        logger.info(
                            f"Skipping {resource_category} (not {resource_type})"
                        )
                else:
                    logger.info(
                        f"Resource identifier doesn't have enough parts: {parts}"
                    )

            # Filter tenants that have both create and update
            result = []
            logger.info(
                f"Checking {len(tenant_scopes)} tenants for create, update access: {list(tenant_scopes.keys())}"
            )
            for tenant, scopes in tenant_scopes.items():
                logger.info(f"Tenant {tenant} has scopes: {scopes}")
                if "create" in scopes and "update" in scopes:
                    result.append(tenant)
                else:
                    logger.info(
                        f"Tenant {tenant} missing create or update: actual scopes are {scopes})"
                    )

            logger.info(
                f"Returning {len(result)} tenants with create/update access: {result}"
            )
            return sorted(result)

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to get tenant access from Keycloak: {e.response.status_code} {e.response.text}"
            )
            if e.response.status_code in (401, 403):
                return []
            raise
        except Exception as e:
            logger.error(f"Error getting tenant access: {e}")
            raise

    def close(self):
        """Close the HTTP client"""
        pass
