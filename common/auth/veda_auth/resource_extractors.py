"""Resource Extractors for PEP Middleware
These functions extract resource identifiers from requests for authorization
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from fastapi import Request

logger = logging.getLogger(__name__)

TENANT_FIELD = os.getenv("VEDA_TENANT_FILTER_FIELD", "eic:tenant")


def extract_stac_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for STAC API requests
    Resource ID format matches Keycloak resource definitions (wildcard patterns):
    - Collections: "stac:collection:{tenant}:*" or "stac:collection:public:*"
    - Items: "stac:item:{tenant}:*" or "stac:item:public:*"
    """
    path = request.url.path
    method = request.method

    match = re.match(r".*?/collections/([^/]+)$", path)
    if match:
        if method in ("PUT", "PATCH"):
            return _extract_collection_resource_id_from_post_body(request)

        # TODO - discuss with team re deletes scenarios
        tenant = getattr(request.state, "tenant", None)
        if tenant:
            return f"stac:collection:{tenant}:*"
        return "stac:collection:public:*"

    match = re.match(r".*?/collections/([^/]+)/items/([^/]+)$", path)
    if match:
        tenant = getattr(request.state, "tenant", None)
        if tenant:
            return f"stac:item:{tenant}:*"
        return "stac:item:public:*"

    match = re.match(r".*?/collections/([^/]+)/items$", path)
    if match:
        tenant = getattr(request.state, "tenant", None)
        if tenant:
            return f"stac:collection:{tenant}:*"
        return "stac:collection:public:*"

    match = re.match(r".*?/collections/([^/]+)/bulk_items$", path)
    if match:
        tenant = getattr(request.state, "tenant", None)
        if tenant:
            return f"stac:collection:{tenant}:*"
        return "stac:collection:public:*"

    if "/queryables" in path or "/search" in path:
        return None

    return None


def _extract_tenant_from_body(
    body_data: Dict[str, Any], tenant_field: Optional[str] = None
) -> Optional[str]:
    """Extract tenant from request body JSON data"""
    if tenant_field is None:
        tenant_field = TENANT_FIELD

    try:
        tenant = body_data.get(tenant_field)
        if tenant:
            return tenant

        properties = body_data.get("properties", {})
        if isinstance(properties, dict):
            tenant = properties.get(tenant_field)
            if tenant:
                return tenant

        return None
    except (AttributeError, TypeError) as e:
        logger.debug(f"Failed to extract tenant from body: {e}")
        return None


def _extract_collection_resource_id_from_post_body(request: Request) -> Optional[str]:
    """Extract collection resource ID from POST/PUT collections request body"""
    try:
        cached_body = getattr(request.state, "_cached_body", None)
        if not cached_body:
            logger.warning(
                "Cannot extract resource ID: body not cached for collection operation"
            )
            return None

        body_data = json.loads(cached_body)

        tenant = _extract_tenant_from_body(body_data)
        if tenant:
            return f"stac:collection:{tenant}:*"
        else:
            return "stac:collection:public:*"
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.warning(f"Failed to extract resource ID from collection body: {e}")
        return None


def extract_ingest_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for Ingest API requests
    Resource ID format matches Keycloak resource definitions (wildcard patterns):
    - Collections: "stac:collection:{tenant}:*" or "stac:collection:public:*" (POST only)
    - Collections: "stac:collection:{collection_id}" (DELETE only)
    - Items: "stac:item:*"
    """
    path = request.url.path
    method = request.method

    if path.endswith("/collections") and method == "POST":
        return _extract_collection_resource_id_from_post_body(request)

    match = re.match(r".*?/collections/([^/]+)$", path)
    if match and method == "DELETE":
        collection_id = match.group(1)
        return f"collection:{collection_id}"

    if match:
        # GET /collections/{id} - not used in ingest API but handle for completeness
        collection_id = match.group(1)
        return f"collection:{collection_id}"

    if path.endswith("/items") and method == "POST":
        return "item:*"

    return None
