"""
Tenant Links Middleware for STAC API

This middleware detects tenant URLs and modifies the response to add tenant in the links.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

from stac_auth_proxy.utils.middleware import JsonResponseMiddleware
from stac_auth_proxy.utils.stac import get_links

from fastapi import FastAPI, Request
from starlette.datastructures import Headers
from starlette.types import Scope

logger = logging.getLogger(__name__)


@dataclass
class TenantLinksMiddleware(JsonResponseMiddleware):
    """
    Middleware adds tenant in the links in the response content
    """

    app: FastAPI
    root_path: str = ""
    json_content_type_expr: str = r"application/(geo\+)?json"

    def should_transform_response(self, request: Request, scope: Scope) -> bool:
        """Only transform responses with JSON content type."""
        return all(
            [
                re.match(
                    self.json_content_type_expr,
                    Headers(scope=scope).get("content-type", ""),
                ),
                # Only transform responses for requests that have an associated tenant
                hasattr(request.state, "tenant"),
            ]
        )

    def transform_json(self, data: dict[str, Any], request: Request) -> dict[str, Any]:
        """Update links in the response to include root_path."""
        # Get the client's actual base URL (accounting for load balancers/proxies)
        tenant = request.state.tenant
        for link in get_links(data):
            try:
                self._update_link(link, tenant)
            except Exception as e:
                logger.error(
                    "Failed to parse link href %r, (ignoring): %s",
                    link.get("href"),
                    str(e),
                )
        return data

    def _update_link(self, link: dict[str, Any], tenant: str) -> None:
        """Update link to include tenant."""
        url_parsed = urlparse(link["href"])
        # /api/stac/collections -> /collections
        path_without_root_path = url_parsed.path[len(self.root_path) :]
        # /collections -> /api/stac/{tenant}/collections
        url_parsed = url_parsed._replace(
            path=f"{self.root_path}/{tenant}{path_without_root_path}"
        )
        logger.debug("Updated link %r to %r", link["href"], urlunparse(url_parsed))
        link["href"] = urlunparse(url_parsed)
