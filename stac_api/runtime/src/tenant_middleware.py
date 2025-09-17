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
            tenant = self._extract_tenant(request)

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

    def _extract_tenant(self, request: Request) -> Optional[str]:
        """Extracts the tenant identifier from the URL"""
        path = request.url.path
        if path.startswith("/api/stac/"):
            path_parts = path.replace("/api/stac/", "").split("/")
            if path_parts and path_parts[0]:
                return path_parts[0]
        return None
