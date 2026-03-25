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
from typing import Any, Awaitable, Callable, Dict, Optional

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

CollectionTenantResolver = Callable[[Request, str], Awaitable[Optional[str]]]

_COLLECTIONS_CREATE_PATH_PATTERN = re.compile(COLLECTIONS_CREATE_PATH_RE)
_COLLECTIONS_PATH_PATTERN = re.compile(COLLECTIONS_PATH_RE)
_COLLECTIONS_ITEM_PATH_PATTERN = re.compile(COLLECTIONS_ITEM_PATH_RE)
_COLLECTIONS_ITEMS_PATH_PATTERN = re.compile(COLLECTIONS_ITEMS_PATH_RE)
_COLLECTIONS_BULK_ITEMS_PATH_PATTERN = re.compile(COLLECTIONS_BULK_ITEMS_PATH_RE)


def _stac_collection_resource_id(request: Request) -> str:
    """Return tenant-based or public STAC collection resource ID."""
    tenant = getattr(request.state, "tenant", None)
    if not isinstance(tenant, str) or not tenant:
        return STAC_COLLECTION_PUBLIC
    return STAC_COLLECTION_TEMPLATE.format(tenant)


def _stac_item_resource_id(request: Request) -> str:
    """Return tenant-based or public STAC item resource ID."""
    tenant = getattr(request.state, "tenant", None)
    if not isinstance(tenant, str) or not tenant:
        return STAC_ITEM_PUBLIC
    return STAC_ITEM_TEMPLATE.format(tenant)


def _get_collection_tenant_resolver(
    request: Request,
) -> Optional[CollectionTenantResolver]:
    """Return optional collection-tenant resolver from app state if configured"""
    app = getattr(request, "app", None)
    if app is None:
        return None
    state = getattr(app, "state", None)
    return getattr(state, "collection_tenant_resolver", None)


async def _collection_tenant_for_item(
    request: Request, collection_id: str
) -> Optional[str]:
    """Resolve collection tenant for item operations"""
    resolver = _get_collection_tenant_resolver(request)
    if not resolver:
        logger.debug(
            "No collection_tenant_resolver configured on app.state for collection %s",
            collection_id,
        )
        return None
    try:
        tenant = await resolver(request, collection_id)
        if not tenant:
            logger.debug(
                "collection_tenant_resolver returned no tenant for collection %s",
                collection_id,
            )
        return tenant
    except Exception as e:
        logger.warning(
            "Failed to resolve collection tenant for item ops %s: %s",
            collection_id,
            e,
            exc_info=True,
        )
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


async def _extract_collection_stac_resource_id(
    request: Request, path: str, method: str
) -> Optional[str]:
    """Extract resource ID for collection endpoints, or None if not a collection path"""
    if _COLLECTIONS_CREATE_PATH_PATTERN.match(path) and method == "POST":
        return await _extract_collection_resource_id_from_post_body(request)

    match = _COLLECTIONS_PATH_PATTERN.match(path)
    if match:
        if method in ("PUT", "PATCH"):
            return await _extract_collection_resource_id_from_post_body(request)
        if method == "DELETE":
            collection_id = match.group(1)
            tenant = await _collection_tenant_for_item(request, collection_id)
            if tenant:
                return STAC_COLLECTION_TEMPLATE.format(tenant)
            return _stac_collection_resource_id(request)
        return _stac_collection_resource_id(request)

    return None


async def _extract_item_stac_resource_id(
    request: Request, path: str, method: str
) -> Optional[str]:
    """Extract resource ID for item endpoints, or None if not an item path"""
    if _COLLECTIONS_ITEM_PATH_PATTERN.match(path):
        # For single item operations, prefer collection tenant when available
        match = _COLLECTIONS_ITEM_PATH_PATTERN.match(path)
        collection_id = match.group(1) if match else None
        if collection_id:
            tenant = await _collection_tenant_for_item(request, collection_id)
            if tenant:
                return STAC_ITEM_TEMPLATE.format(tenant)
        return _stac_item_resource_id(request)

    if _COLLECTIONS_ITEMS_PATH_PATTERN.match(path):
        # use collection tenant when available, otherwise collection/public
        match = _COLLECTIONS_ITEMS_PATH_PATTERN.match(path)
        collection_id = match.group(1) if match else None
        if collection_id:
            tenant = await _collection_tenant_for_item(request, collection_id)
            if tenant:
                return STAC_ITEM_TEMPLATE.format(tenant)
        return _stac_collection_resource_id(request)

    if _COLLECTIONS_BULK_ITEMS_PATH_PATTERN.match(path):
        match = _COLLECTIONS_BULK_ITEMS_PATH_PATTERN.match(path)
        collection_id = match.group(1) if match else None
        if collection_id:
            tenant = await _collection_tenant_for_item(request, collection_id)
            if tenant:
                return STAC_ITEM_TEMPLATE.format(tenant)
        return _stac_collection_resource_id(request)

    return None


async def extract_stac_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for STAC API requests

    Resource ID format matches Keycloak resource definitions (wildcard patterns):
    - Collections: STAC_COLLECTION_TEMPLATE or STAC_COLLECTION_PUBLIC
    - Items: STAC_ITEM_TEMPLATE or STAC_ITEM_PUBLIC
    """
    path = request.url.path
    method = request.method

    collection_id = await _extract_collection_stac_resource_id(request, path, method)
    if collection_id is not None:
        return collection_id

    item_id = await _extract_item_stac_resource_id(request, path, method)
    if item_id is not None:
        return item_id

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
        tenant = await _collection_tenant_for_item(request, collection_id)
        if tenant:
            resource_id = STAC_COLLECTION_TEMPLATE.format(tenant)
            logger.debug(
                "Ingest DELETE /collections/%s: resolved tenant=%s -> %s",
                collection_id,
                tenant,
                resource_id,
            )
            return resource_id
        fallback_resource_id = _stac_collection_resource_id(request)
        logger.info(
            "Ingest DELETE /collections/%s: falling back to resource_id=%s (resolver_none_or_missing), path=%s",
            collection_id,
            fallback_resource_id,
            path,
        )
        return fallback_resource_id

    return None
