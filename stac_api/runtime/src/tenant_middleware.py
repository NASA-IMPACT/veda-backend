""" Tenant Middleware for STAC API. Useful for extracting tenant information """
import logging
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .tenant_models import TenantContext, TenantValidationError

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant-aware STAC API request processing.

    This middleware extracts the tenant identifier from the URL path and creates a context
    for downstream processing. It also handles valiadtion errors.

    It will process requests by:
    - extracting the tenant from the URL path (/api/stac/{tenant}/...)
    - creating a TenantContext with the tenant ID and correlation ID
    - handle validation errors

    """

    def __init__(self, app):
        """Initializes the tenant middleware"""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Processes incoming requests and extracts the tenant identifier from the URL"""

        try:
            if self._should_skip_tenant_processing(request):
                return await call_next(request)

            tenant = self._extract_tenant(request)
            logger.info(f"Extracted tenant is {tenant}")

            tenant_context = (
                TenantContext(
                    tenant_id=tenant,
                    request_id=request.headers.get("X-Correlation-ID"),
                )
                if tenant
                else None
            )

            request.state.tenant_context = tenant_context

            if tenant:
                logger.info(
                    f"Tenant access: {tenant} for {request.method} {request.url.path}",
                    extra={
                        "tenant": tenant,
                        "method": request.method,
                        "path": request.url.path if tenant_context else None,
                    },
                )

            response = await call_next(request)

            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                if tenant_context.request_id:
                    response.headers["X-Request-ID"] = tenant_context.request_id

            return response

        except TenantValidationError as e:
            logger.warning(
                f"Tenant validation failed: {e.detail}",
                extra={
                    "tenant": getattr(e, "tenant", None),
                    "resource_type": getattr(e, "resource_type", None),
                    "resource_id": getattr(e, "resource_id", None),
                },
            )
            raise HTTPException(status_code=404, detail=e.detail)

        except Exception as e:
            logger.error(f"Tenant middleware error: {str(e)}")
            raise

    def _should_skip_tenant_processing(self, request: Request) -> bool:
        """Check if tenant processing should be skipped for this request"""
        path = request.url.path
        logger.info(f"Tenant middleware processing path: {path}")

        # handles both local (no prefix) and production (/api/stac/ prefix) environments
        if path.startswith("/api/stac/"):
            if path == "/api/stac/" or path == "/api/stac":
                logger.info(f"Skipping tenant processing - root STAC API: {path}")
                return True

            path_parts = path.replace("/api/stac/", "").split("/")
        else:
            path_parts = path.lstrip("/").split("/")

        logger.info(f"Path parts: {path_parts}")

        if not path_parts or not path_parts[0]:
            logger.info(f"Skipping tenant processing - empty path parts: {path}")
            return True

        standard_endpoints = {
            "collections",
            "conformance",
            "search",
            "queryables",
            "openapi.json",
            "docs",
            "favicon.ico",
            "health",
            "ping",
        }

        first_part = path_parts[0].rstrip("/")
        logger.info(
            f"First part: '{path_parts[0]}', stripped: '{first_part}', in standard_endpoints: {first_part in standard_endpoints}"
        )

        # if the path is exactly a standard endpoint with trailing slash, skip tenant processing
        if len(path_parts) == 2 and path_parts[1] == "" and first_part in standard_endpoints:
            logger.info(f"Skipping tenant processing for standard endpoint with trailing slash: {first_part}/")
            return True

        if first_part in standard_endpoints:
            logger.info(
                f"Skipping tenant processing for standard endpoint: {first_part}"
            )
            return True

        logger.info(f"Processing as tenant: {first_part}")
        return False

    def _extract_tenant(self, request: Request) -> Optional[str]:
        """Extracts the tenant identifier from the URL"""
        path = request.url.path
        logger.info(f"Extracting tenant from request path {path}")
        if path.startswith("/api/stac/"):
            path_parts = path.replace("/api/stac/", "").split("/")
            if path_parts and path_parts[0]:
                return path_parts[0]
        return None
