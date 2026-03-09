"""" Resource Extractors to use in PEP Middleware.
We need to extract the following from a request in order to create a permission ticket request:
- resource id
- scope
- tenant
https://www.keycloak.org/docs/latest/authorization_services/index.html#creating-permission-ticket
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

TENANT_FIELD = os.getenv("VEDA_TENANT_FILTER_FIELD", "eic:tenant")
STAC_COLLECTION_PUBLIC = "stac:collection:public:*"
STAC_ITEM_PUBLIC = "stac:item:public:*"
STAC_COLLECTION_TEMPLATE = "stac:collection:{}:*"
STAC_ITEM_TEMPLATE = "stac:item:{}:*"

COLLECTIONS_CREATE_PATH_RE = r".*?/collections$"
COLLECTIONS_PATH_RE = r".*?/collections/([^/]+)$"
COLLECTIONS_ITEM_PATH_RE = r".*?/collections/([^/]+)/items/([^/]+)$"
COLLECTIONS_ITEMS_PATH_RE = r".*?/collections/([^/]+)/items$"
COLLECTIONS_BULK_ITEMS_PATH_RE = r".*?/collections/([^/]+)/bulk_items$"

_COLLECTIONS_CREATE_PATH_PATTERN = re.compile(COLLECTIONS_CREATE_PATH_RE)
_COLLECTIONS_PATH_PATTERN = re.compile(COLLECTIONS_PATH_RE)
_COLLECTIONS_ITEM_PATH_PATTERN = re.compile(COLLECTIONS_ITEM_PATH_RE)
_COLLECTIONS_ITEMS_PATH_PATTERN = re.compile(COLLECTIONS_ITEMS_PATH_RE)
_COLLECTIONS_BULK_ITEMS_PATH_PATTERN = re.compile(COLLECTIONS_BULK_ITEMS_PATH_RE)


def _stac_collection_resource_id(request: Request) -> str:
    """Return tenant-based or public STAC collection resource ID."""
    tenant = getattr(request.state, "tenant", None)
    return STAC_COLLECTION_TEMPLATE.format(tenant) if tenant else STAC_COLLECTION_PUBLIC


def _stac_item_resource_id(request: Request) -> str:
    """Return tenant-based or public STAC item resource ID."""
    tenant = getattr(request.state, "tenant", None)
    return STAC_ITEM_TEMPLATE.format(tenant) if tenant else STAC_ITEM_PUBLIC


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

        return None
    except (AttributeError, TypeError) as e:
        logger.debug(f"Failed to extract tenant from body: {e}")
        return None


async def _extract_collection_resource_id_from_post_body(
    request: Request,
) -> Optional[str]:
    """Extract collection resource ID from POST/PUT collections request body"""
    try:
        request_body = await request.body()
        if not request_body:
            raise HTTPException(
                status_code=400,
                detail="Cannot extract resource ID: empty body for collection operation",
            )

        body_data = json.loads(request_body)
        tenant = _extract_tenant_from_body(body_data)
        if tenant:
            return STAC_COLLECTION_TEMPLATE.format(tenant)
        return STAC_COLLECTION_PUBLIC
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.warning(f"Failed to extract resource ID from collection body: {e}")
        return None


async def extract_stac_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for STAC API requests
    Resource ID format matches Keycloak resource definitions (wildcard patterns):
    - Collections: STAC_COLLECTION_TEMPLATE or STAC_COLLECTION_PUBLIC
    - Items: STAC_ITEM_TEMPLATE or STAC_ITEM_PUBLIC
    """
    path = request.url.path
    method = request.method

    if _COLLECTIONS_CREATE_PATH_PATTERN.match(path) and method == "POST":
        return await _extract_collection_resource_id_from_post_body(request)

    if _COLLECTIONS_PATH_PATTERN.match(path):
        if method in ("PUT", "PATCH"):
            return await _extract_collection_resource_id_from_post_body(request)
        return _stac_collection_resource_id(request)

    if _COLLECTIONS_ITEM_PATH_PATTERN.match(path):
        return _stac_item_resource_id(request)

    if _COLLECTIONS_ITEMS_PATH_PATTERN.match(
        path
    ) or _COLLECTIONS_BULK_ITEMS_PATH_PATTERN.match(path):
        return _stac_collection_resource_id(request)

    if "/queryables" in path or "/search" in path:
        return None

    return None


async def extract_ingest_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for Ingest API requests"""
    path = request.url.path
    method = request.method

    if path.endswith("/collections") and method == "POST":
        return await _extract_collection_resource_id_from_post_body(request)

    match = re.match(r".*?/collections/([^/]+)$", path)
    if match and method == "DELETE":
        collection_id = match.group(1)
        return f"collection:{collection_id}"

    return None
