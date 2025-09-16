import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .tenant_models import TenantContext

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        try:
            tenant = self._extract_tenant(request)

            tenant_context = TenantContext(
                tenant_id=tenant,
                request_id=request.headers.get("X-Correlation-ID"),
            ) if tenant else None

            request.state.tenant_context = tenant_context

            if tenant:
                logger.info(
                    f"Tenant access: {tenant} for {request.method} {request.url.path}",
                    extra={
                        "tenant": tenant,
                        "method": request.method,
                        "path": request.url.path if tenant_context else None
                    }
                )

            response = await call_next(request)

            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                if tenant_context.request_id:
                    response.headers["X-Request-ID"] = tenant_context.request_id

            return response

        except Exception as e:
        # JT TODO - Put more helpful exception?
            logger.warning(
                f"Tenant validation failed: {e.detail}",
                extra={
                    "tenant": getattr(e, 'tenant', None),
                    "resource_type": getattr(e, 'resource_type', None),
                    "resource_id": getattr(e, 'resource_id', None)
                }
            )
            raise HTTPException(status_code=404, detail=e.detail)

        except Exception as e:
            logger.error(f"Tenant middleware error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _extract_tenant(self, request: Request) -> Optional[str]:
        path = request.url.path
        if path.startswith('/api/stac/'):
            path_parts = path.replace('/api/stac/', '').split('/')
            if path_parts and path_parts[0]:
                return path_parts[0]
        return None