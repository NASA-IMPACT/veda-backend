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

from .tenant_models import TenantContext

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
    root_path: str = ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Extract tenant from path"""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        original_path = scope["path"]
        if original_path.endswith("/") and original_path not in [
            "/",
            f"{self.root_path}",
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
        tenant_context = (
            TenantContext(
                tenant_id=tenant,
                request_id=request.headers.get("X-Correlation-ID"),
            )
            if tenant
            else None
        )

        request.state.tenant_context = tenant_context
        request.state.tenant = tenant

        logger.debug(
            f"Tenant access: {tenant} for {request.method} {request.url.path}",
            extra={
                "tenant": tenant,
                "method": request.method,
                "path": request.url.path if tenant_context else None,
            },
        )

        logger.debug("Removing tenant %s from path %r", tenant, request.url.path)
        scope["path"] = self._remove_tenant_from_path(request.url.path, tenant)
        logger.debug("New path is %s", scope["path"])

        return await self.app(scope, receive, send)

    def _extract_tenant_from_path(self, request: Request) -> Optional[str]:
        """Extracts the tenant identifier from the URL"""
        path = (
            request.url.path[len(self.root_path) :]
            if self.root_path and request.url.path.startswith(self.root_path)
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

    def _remove_tenant_from_path(self, path: str, tenant: str) -> str:
        """Remove the tenant from the path"""
        return (
            self.root_path + path[len(f"{self.root_path}/{tenant}") :]
            if self.root_path and path.startswith(f"{self.root_path}/{tenant}")
            else path[len(f"/{tenant}") :]
        )
