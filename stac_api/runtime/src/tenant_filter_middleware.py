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

from .tenant_models import TenantContext

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
        """Initialize tenant filter middleware"""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request,  add tenant filtering if needed"""
        try:
            if self._should_skip_tenant_processing(request):
                return await call_next(request)

            tenant = self._extract_tenant_from_path(request)
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
                # Apply tenant filtering to the request
                request = self._add_tenant_filter_to_request(request, tenant)

            response = await call_next(request)

            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                if tenant_context.request_id:
                    response.headers["X-Request-ID"] = tenant_context.request_id

                response = await self._rewrite_response_content(
                    response, tenant_context.tenant_id
                )

            return response

        except Exception as e:
            logger.error(f"Tenant middleware error: {str(e)}")
            raise

    def _extract_tenant_from_path(self, request: Request) -> Optional[str]:
        """Extracts the tenant identifier from the URL"""
        path = request.url.path
        logger.info(f"Extracting tenant from request path {path}")

        # Handle both production (/api/stac/{tenant}/) and local (/{tenant}/) patterns
        if path.startswith("/api/stac/"):
            path_parts = path.replace("/api/stac/", "").split("/")
            if path_parts and path_parts[0]:
                return path_parts[0]
        elif path.startswith("/") and not path.startswith("/api/stac/"):
            # Local development: /{tenant}/collections
            path_parts = path.lstrip("/").split("/")
            if path_parts and path_parts[0]:
                # Check if it's not a standard endpoint
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
                if path_parts[0] not in standard_endpoints:
                    return path_parts[0]
        return None

    def _add_tenant_filter_to_request(self, request: Request, tenant: str) -> Request:
        """Add CQL2 filter to the request for tenant filtering in cql2 text format"""
        try:
            parsed_url = urlparse(str(request.url))
            query_params = parse_qs(parsed_url.query)

            # Validate tenant parameter
            if not tenant or not tenant.strip():
                logger.warning("Empty tenant provided for filtering")
                return request

            tenant_filter_text = f"dashboard:tenant = '{tenant}'"

            if "filter" in query_params:
                existing_filter = query_params["filter"][0]
                combined_filter = f"({existing_filter}) AND ({tenant_filter_text})"
                query_params["filter"] = [combined_filter]
            else:
                query_params["filter"] = [tenant_filter_text]

            query_params["filter-lang"] = ["cql2-text"]

            new_query = urlencode(query_params, doseq=True)
        except Exception as e:
            logger.error(f"Error adding tenant filter: {str(e)}")
            return request

        # handle URL rewriting for both root path and non root path environments
        if parsed_url.path.startswith(f"/api/stac/{tenant}/"):
            # example /api/stac/{tenant}/collections -> /api/stac/collections
            new_path = parsed_url.path.replace(f"/api/stac/{tenant}/", "/api/stac/")
        elif parsed_url.path.startswith(f"/{tenant}/"):
            # example /{tenant}/collections -> /collections
            new_path = parsed_url.path.replace(f"/{tenant}/", "/")
        else:
            new_path = parsed_url.path

        logger.info(f"TENANT MIDDLEWARE Original path: {parsed_url.path}")
        logger.info(f"TENANT MIDDLEWARE New path: {new_path}")
        logger.info(f"TENANT MIDDLEWARE Tenant: {tenant}")

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
        logger.debug(f"Generated URL {new_url}")

        new_url_obj = URL(new_url)
        logger.debug(f"New URL object path: {new_url_obj.path}")
        logger.debug(f"New URL object query: {new_url_obj.query}")

        request.scope["path"] = new_url_obj.path
        request.scope["query_string"] = new_url_obj.query.encode()

        return request

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
        if (
            len(path_parts) == 2
            and path_parts[1] == ""
            and first_part in standard_endpoints
        ):
            logger.info(
                f"Skipping tenant processing for standard endpoint with trailing slash: {first_part}/"
            )
            return True

        if first_part in standard_endpoints:
            logger.info(
                f"Skipping tenant processing for standard endpoint: {first_part}"
            )
            return True

        logger.info(f"Processing as tenant: {first_part}")
        return False

    async def _rewrite_response_content(self, response, tenant: str):
        """This function rewrites response content to include tenant in URLs if tenant was passed in"""
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                import json

                try:
                    data = json.loads(body.decode())
                    rewritten_data = self._rewrite_json_urls(data, tenant)
                    rewritten_body = json.dumps(rewritten_data).encode()

                    from starlette.responses import Response

                    headers = dict(response.headers)
                    headers.pop("content-length", None)
                    new_response = Response(
                        content=rewritten_body,
                        status_code=response.status_code,
                        headers=headers,
                        media_type=response.media_type,
                    )
                    return new_response
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response for URL rewriting")
                    return response
            else:
                return response
        except Exception as e:
            logger.error(f"Error rewriting response content: {str(e)}")
            return response

    def _rewrite_json_urls(self, data, tenant: str):
        """Recursively rewrites URLs in JSON data to include tenant in the url"""
        if isinstance(data, dict):
            rewritten = {}
            for key, value in data.items():
                if key == "href" and isinstance(value, str):
                    # Rewrite href URLs to include tenant
                    rewritten[key] = self._add_tenant_to_url(value, tenant)
                else:
                    rewritten[key] = self._rewrite_json_urls(value, tenant)
            return rewritten
        elif isinstance(data, list):
            return [self._rewrite_json_urls(item, tenant) for item in data]
        else:
            return data

    def _add_tenant_to_url(self, url: str, tenant: str) -> str:
        """Add tenant to URL if it is a STAC API URL"""
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)

            # Check if this is a STAC API URL that needs tenant rewriting
            if "/api/stac/" in parsed.path:
                # Rewrite /api/stac/collections -> /api/stac/{tenant}/collections
                new_path = parsed.path.replace("/api/stac/", f"/api/stac/{tenant}/")
                return urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        new_path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            elif parsed.path.startswith("/collections") or parsed.path.startswith(
                "/search"
            ):
                # For local development: /collections -> /{tenant}/collections
                new_path = f"/{tenant}{parsed.path}"
                return urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        new_path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            else:
                # Return original URL if there is no rewriting needed
                return url
        except Exception as e:
            logger.error(f"Error rewriting URL {url}: {str(e)}")
            return url
