"""
Tenant Filter Middleware for STAC API

This middleware detects tenant URLs and modifies the request to add CQL2 filters
for tenant filtering
"""

import logging
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastapi import Request
from starlette.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TenantFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that detects tenant URLs and modifies requests to add CQL2 filters

    This middleware:
    - detects URLs like /api/stac/{tenant}/collections
    - extracts the tenant from the URL path
    - modifies the request to add CQL2 filter for keywords
    - redirects to the regular collections endpoint
    """

    def __init__(self, app):
        """Initialize tenant filter middlewar"""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request,  add tenant filtering if needed"""

        logger.info(f"Middleware processing: {request.method} {request.url.path}")
        print(f"DEBUG processing URL: {request.url.path}")

        # Check if this is a tenant URL
        tenant = self._extract_tenant_from_path(request.url.path)
        print(f"DEBUG extracted tenant: {tenant}")

        if tenant:
            logger.info(
                f"Tenant detected: {tenant} for {request.method} {request.url.path}"
            )

            # Modify the request to add CQL2 filter
            modified_request = self._add_tenant_filter_to_request(request, tenant)

            # Process the modified request
            response = await call_next(modified_request)

            # Add tenant header to response
            response.headers["X-Tenant-ID"] = tenant

            return response

        logger.info(f"No tenant detected for: {request.method} {request.url.path}")
        return await call_next(request)

    def _extract_tenant_from_path(self, path: str) -> Optional[str]:
        """Extract tenant from URL path"""
        parts = path.strip("/").split("/")
        print(f"DEBUG URL parts: {parts}")

        # this condition handles /api/stac/{tenant}/collections pattern
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "stac":
            known_endpoints = [
                "collections",
                "search",
                "queryables",
                "conformance",
                "docs",
                "openapi.json",
            ]
            if parts[2] not in known_endpoints:
                return parts[2]

        # this condition handles /{tenant}/collections pattern (no api/stac prefix)
        elif len(parts) >= 2:
            known_endpoints = [
                "collections",
                "search",
                "queryables",
                "conformance",
                "docs",
                "openapi.json",
                "api",
            ]
            if parts[0] not in known_endpoints:
                return parts[0]

        return None

    def _add_tenant_filter_to_request(self, request: Request, tenant: str) -> Request:
        """Add CQL2 filter to the request for tenant filtering in cql2 text format"""

        parsed_url = urlparse(str(request.url))
        query_params = parse_qs(parsed_url.query)

        tenant_filter_text = f"dashboard:tenant = '{tenant}'"

        if "filter" in query_params:
            existing_filter = query_params["filter"][0]
            combined_filter = f"({existing_filter}) AND ({tenant_filter_text})"
            query_params["filter"] = [combined_filter]
        else:
            query_params["filter"] = [tenant_filter_text]

        query_params["filter-lang"] = ["cql2-text"]

        new_query = urlencode(query_params, doseq=True)

        if parsed_url.path.startswith(f"/api/stac/{tenant}/"):
            new_path = parsed_url.path.replace(f"/api/stac/{tenant}/", "/api/stac/")
        elif parsed_url.path.startswith(f"/{tenant}/"):
            new_path = parsed_url.path.replace(f"/{tenant}/", "/")
        else:
            new_path = parsed_url.path

        print(f"DEBUG original path: {parsed_url.path}")
        print(f"DEBUG new path: {new_path}")

        new_url = urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                new_path,
                parsed_url.params,
                new_query,
                parsed_url.fragment,
            )
        )
        print(f"NEWLY GENERATED URL {new_url}")

        new_url_obj = URL(new_url)
        print(f"DEBUG new URL object path: {new_url_obj.path}")
        print(f"DEBUG new URL object query: {new_url_obj.query}")

        new_scope = request.scope.copy()
        new_scope["path"] = new_url_obj.path
        new_scope["query_string"] = new_url_obj.query.encode()
        print(f"DEBUG new scope path: {new_scope['path']}")
        print(f"DEBUG new scope query_string: {new_scope['query_string']}")

        request.scope["path"] = new_url_obj.path
        request.scope["query_string"] = new_url_obj.query.encode()

        return request
