"""Policy Enforcement Point (PEP) middleware proof of concept"""

import re
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from veda_auth.keycloak_client import KeycloakPDPClient, TokenError
from veda_auth.resource_extractors import (
    COLLECTIONS_CREATE_PATH_RE,
    extract_stac_resource_id,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProtectedRoute:
    """Routes protected by policy decision point

    path_re: regex pattern applied to request path
    method: HTTP method
    scope: Keycloak resource scope name to check (e.g. "create", "update", "delete")
    """

    path_re: str
    method: str
    scope: str

DEFAULT_PROTECTED_ROUTES: Sequence[ProtectedRoute] = (
    ProtectedRoute(path_re=COLLECTIONS_CREATE_PATH_RE, method="POST", scope="create"),
)


class PEPMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces UMA authorization"""

    def __init__(
        self,
        app: ASGIApp,
        *,
        pdp_client: Callable[[], KeycloakPDPClient],
        protected_routes: Optional[Sequence[ProtectedRoute]] = None,
    ):
        super().__init__(app)
        self._get_pdp_client = pdp_client
        routes = protected_routes if protected_routes is not None else DEFAULT_PROTECTED_ROUTES
        self._compiled = [
            (re.compile(r.path_re), r.method.upper(), r.scope) for r in routes
        ]

    def _get_matching_scope_and_route(self, request: Request) -> Optional[tuple[str, str]]:
        """Return (scope, method) for the route that matches, otherwise return None"""
        path = request.url.path.rstrip("/") or "/"
        method = request.method.upper()
        for pattern, route_method, scope in self._compiled:
            if route_method == method and pattern.search(path):
                return (scope, route_method)
        return None

    def _get_bearer_token(self, request: Request) -> Optional[str]:
        """Extract the Bearer token from the Authorization header"""
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        return auth[7:].strip()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        matched_request = self._get_matching_scope_and_route(request)
        if matched_request is None:
            logger.debug(
                "PEP: no protected route match for %s %s... continuing",
                request.method, request.url.path,
            )
            return await call_next(request)

        scope, _method = matched_request
        logger.info(
            "PEP: matched protected route %s %s and scope=%s",
            _method, request.url.path, scope,
        )

        pdp_client = self._get_pdp_client()

        token = self._get_bearer_token(request)
        if not token:
            logger.warning("PEP: missing Bearer token for %s %s", _method, request.url.path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing or invalid Authorization header (Bearer token required)"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        resource_id = await extract_stac_resource_id(request)
        if not resource_id:
            logger.warning("PEP: no resource ID for %s %s", _method, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Could not determine resource for authorization"},
            )

        logger.info(
            "PEP: checking permission resource_id=%s, scope=%s, path=%s",
            resource_id, scope, request.url.path,
        )

        try:
            authorized = pdp_client.check_permission(
                access_token=token,
                resource_id=resource_id,
                scope=scope,
            )
        except TokenError as e:
            logger.warning(
                "PEP: token error for %s %s: %s", _method, request.url.path, e.detail
            )
            return JSONResponse(
                status_code=401,
                content={"detail": e.detail},
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        except Exception as e:
            logger.exception("PEP: Keycloak check failed for resource_id=%s scope=%s: %s", resource_id, scope, e)
            return JSONResponse(
                status_code=502,
                content={"detail": "Authorization service temporarily unavailable"},
            )

        logger.info(
            "PEP: authorization result=%s for resource_id=%s, scope=%s, path=%s",
            authorized, resource_id, scope, request.url.path,
        )

        if not authorized:
            logger.warning(
                "PEP: denied %s %s  resource_id=%s, scope=%s",
                _method, request.url.path, resource_id, scope,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"You do not have permission to {scope} this resource "
                        f"({resource_id}). Verify that your user belongs to "
                        f"the required tenant and role needed."
                    )
                },
            )

        return await call_next(request)
