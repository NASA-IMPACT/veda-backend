"""
Tenant Filter Middleware for STAC API

This middleware detects tenant URLs and modifies the request to add CQL2 filters
for tenant filtering
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Set

from fastapi import FastAPI, Request
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantExtractionMiddleware:
    """
    Middleware that detects tenant URLs and stores it in the request state

    This middleware:
    - detects URLs like /api/stac/{tenant}/collections
    - extracts the tenant from the URL path
    - removes the tenant from the URL path
    """

    app: FastAPI
    standard_endpoints: Set[str] = field(
        default_factory=lambda: {
            "collections",
            "conformance",
            "search",
            "queryables",
            "openapi.json",
            "docs",
            "health",
            "ping",
            "index.html",
            "_mgmt",
        }
    )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Extract tenant from path"""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        root_path = scope.get("root_path", "")

        original_path = scope["path"]
        if original_path.endswith("/") and original_path not in [
            "/",
            root_path,
        ]:
            logger.debug(f"{original_path=}")
            scope["path"] = original_path.rstrip("/")
            logger.debug(f"Removed trailing slash so now path is {scope['path']}")

        request = Request(scope)

        tenant = self._extract_tenant_from_path(request)

        if not tenant:
            logger.debug("No tenant extracted from %s", request.url.path)
            return await self.app(scope, receive, send)

        logger.debug("Extracted tenant is %s", tenant)
        request.state.tenant = tenant

        logger.debug(
            f"Tenant access: {tenant} for {request.method} {request.url.path}",
            extra={
                "tenant": tenant,
                "method": request.method,
                "path": request.url.path if tenant else None,
            },
        )

        logger.debug("Removing tenant %s from path %r", tenant, request.url.path)
        scope["path"] = (
            root_path + request.url.path[len(f"{root_path}/{tenant}") :]
            if root_path and request.url.path.startswith(f"{root_path}/{tenant}")
            else request.url.path[len(f"/{tenant}") :]
        )
        logger.debug("New path is %s", scope["path"])

        return await self.app(scope, receive, send)

    def _extract_tenant_from_path(self, request: Request) -> Optional[str]:
        """Extracts the tenant identifier from the URL"""
        root_path = request.scope.get("root_path", "")
        path = (
            request.url.path[len(root_path) :]
            if root_path and request.url.path.startswith(root_path)
            else request.url.path
        )
        logger.info("Attempting to extract tenant from request path %s", path)

        # 1. test if first portion of path is in array of known endpoints
        first_part = path.lstrip("/").split("/")[0]
        if first_part in self.standard_endpoints:
            logger.debug(
                "Skipping tenant processing for standard endpoint: %s",
                first_part,
            )
            # 2. first part is a standard endpoint, no tenant
            return None

        # 3. first_part is a tenant, return it
        return first_part
