"""Policy Enforcement Point (PEP) Middleware

This module provides a true PEP middleware that calls Keycloak's PDP
for authorization decisions.
"""

import logging
from typing import Callable, Optional, Set

import httpx

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .keycloak_pdp import KeycloakPDPClient

logger = logging.getLogger(__name__)


class PEPMiddleware(BaseHTTPMiddleware):
    """Policy Enforcement Point middleware that calls Keycloak's PDP

    This middleware:
    1. Extracts the resource being accessed from the request
    2. Calls Keycloak's Authorization Services (PDP) to get authorization decision
    3. Enforces the decision (allow or deny)
    """

    # https://www.keycloak.org/docs/latest/authorization_services/#_resource_overview
    METHOD_TO_SCOPE = {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }

    DEFAULT_PUBLIC_PATHS: Set[str] = {
        "/health",
        "/docs",
        "/openapi.json",
        "/index.html",
    }

    def __init__(
        self,
        app,
        pdp_client: KeycloakPDPClient,
        resource_extractor: Callable[[Request], Optional[str]],
        public_paths: Optional[Set[str]] = None,
    ):
        """
        Args:
            app: FastAPI application
            pdp_client: KeycloakPDPClient instance
            resource_extractor: Function to extract resource_id from request
            public_paths: Set of public paths that don't require authorization
            enable_pep: Whether to enable PEP (should be enabled to use UMA protocol)
        """
        super().__init__(app)
        self.pdp_client = pdp_client
        self.resource_extractor = resource_extractor
        self.public_paths = public_paths or self.DEFAULT_PUBLIC_PATHS

    def _extract_access_token(self, request: Request) -> Optional[str]:
        """Extract access token from Authorization header"""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "").strip()
        return None

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no authorization required)"""
        if path in self.public_paths:
            return True

        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True

        return False

    def _get_scope(self, method: str) -> str:
        """Get UMA scope"""
        return self.METHOD_TO_SCOPE.get(method, "read")

    def _handle_no_access_token(self, path: str, method: str) -> JSONResponse:
        """Handle case when no access token is provided"""
        logger.warning(
            "Authorization failed: No access token provided. Please provide an access token.",
            extra={"path": path, "method": method},
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _handle_no_resource_id(
        self, path: str, method: str, scope: str
    ) -> Optional[JSONResponse]:
        """Handle case when no resource ID can be extracted"""
        if scope == "read":
            logger.debug(
                f"No resource ID extracted for read operation: {path}, allowing request"
            )
            return None  # Allow request
        else:
            logger.warning(
                f"No resource ID extracted for write operation: {path}, denying request",
                extra={"path": path, "method": method, "scope": scope},
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Cannot determine resource for authorization"},
            )

    def _handle_pdp_error(
        self,
        e: httpx.HTTPStatusError,
        path: str,
        method: str,
        resource_id: Optional[str],
    ) -> JSONResponse:
        """Handle errors from Keycloak PDP"""
        if e.response.status_code == 401:
            logger.warning(
                "Keycloak PDP returned 401 ( the token is invalid )",
                extra={"path": path, "method": method},
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif e.response.status_code == 403:
            logger.warning(
                "Keycloak PDP returned 403, permission denied",
                extra={
                    "path": path,
                    "method": method,
                    "resource_id": resource_id,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient permissions"},
            )
        else:
            logger.error(
                f"Keycloak PDP error: {e.response.status_code} {e.response.text}",
                extra={"path": path, "method": method},
            )
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Authorization service error"},
            )

    async def _cache_request_body(self, request: Request) -> None:
        """Cache request body for POST/PUT/PATCH requests so it can be read multiple times"""
        body = await request.body()
        request.state._cached_body = body
        replayed = False

        async def cached_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        request._receive = cached_receive

    async def dispatch(self, request: Request, call_next):
        """PEP (Policy Enforcement Point) middleware that calls Keycloak PDP (Policy Decision Point)"""

        path = request.url.path

        if self._is_public_path(path):
            return await call_next(request)

        scope = self._get_scope(request.method)

        if scope == "read":
            logger.debug(
                "Skipping PEP authorization for read operation (no token required)",
                extra={"path": path, "method": request.method},
            )
            return await call_next(request)

        # Cache request body for POST/PUT/PATCH requests
        if request.method in ("POST", "PUT", "PATCH"):
            await self._cache_request_body(request)

        access_token = self._extract_access_token(request)
        if not access_token:
            return self._handle_no_access_token(path, request.method)

        resource_id = self.resource_extractor(request)

        if not resource_id:
            no_resource_response = self._handle_no_resource_id(
                path, request.method, scope
            )
            if no_resource_response is not None:
                return no_resource_response
            return await call_next(request)

        try:
            has_permission = await self.pdp_client.check_permission(
                access_token=access_token,
                resource_id=resource_id,
                scope=scope,
            )

            if not has_permission:
                logger.warning(
                    "Authorization denied by Keycloak PDP",
                    extra={
                        "path": path,
                        "method": request.method,
                        "resource_id": resource_id,
                        "scope": scope,
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Insufficient permissions for {scope} on {resource_id}"
                    },
                )

            logger.info(
                "Authorization granted by Keycloak PDP",
                extra={
                    "path": path,
                    "method": request.method,
                    "resource_id": resource_id,
                    "scope": scope,
                },
            )

            return await call_next(request)

        except httpx.HTTPStatusError as e:
            return self._handle_pdp_error(e, path, request.method, resource_id)
        except Exception as e:
            logger.error(
                f"PDP authorization check failed: {e}",
                exc_info=True,
                extra={"path": path, "method": request.method},
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authorization service error"},
            )
