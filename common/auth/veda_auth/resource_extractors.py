"""Resource Extractors for PEP Middleware
These functions extract resource identifiers from requests for authorization
"""

import logging
import re
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)


def extract_stac_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for STAC API requests
    Resource ID format matches Keycloak resource definitions:
    - Collections: "stac:collection:{tenant}:{collection_id}" or "stac:collection:public:{collection_id}"
    - Items: "stac:item:{tenant}:{collection_id}:{item_id}" or "stac:item:public:{collection_id}:{item_id}"
    """
    path = request.url.path

    tenant = getattr(request.state, "tenant", None)

    match = re.match(r".*?/collections/([^/]+)$", path)
    if match:
        collection_id = match.group(1)
        if tenant:
            return f"stac:collection:{tenant}:{collection_id}"
        return f"stac:collection:public:{collection_id}"

    match = re.match(r".*?/collections/([^/]+)/items/([^/]+)$", path)
    if match:
        collection_id = match.group(1)
        item_id = match.group(2)
        if tenant:
            return f"stac:item:{tenant}:{collection_id}:{item_id}"
        return f"stac:item:public:{collection_id}:{item_id}"

    match = re.match(r".*?/collections/([^/]+)/items$", path)
    if match:
        collection_id = match.group(1)
        if tenant:
            return f"stac:collection:{tenant}:{collection_id}"
        return f"stac:collection:public:{collection_id}"

    match = re.match(r".*?/collections/([^/]+)/bulk_items$", path)
    if match:
        collection_id = match.group(1)
        if tenant:
            return f"stac:collection:{tenant}:{collection_id}"
        return f"stac:collection:public:{collection_id}"

    if "/queryables" in path or "/search" in path:
        return None

    return None


def extract_ingest_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID for Ingest API requests
    Resource ID format:
    - Collections: "collection:{collection_id}" (for DELETE operations)
    - Items: "item:*" (generic resource for POST /items)
    - Ingestion: "ingestion:{ingestion_id}" or "ingestion:*"
    """
    path = request.url.path
    method = request.method

    match = re.match(r".*?/collections/([^/]+)$", path)
    if match:
        collection_id = match.group(1)
        if method == "DELETE":
            return f"collection:{collection_id}"
        return f"collection:{collection_id}"

    if path.endswith("/items") and method == "POST":
        return "item:*"

    match = re.match(r".*?/ingestions/([^/]+)$", path)
    if match:
        ingestion_id = match.group(1)
        return f"ingestion:{ingestion_id}"

    if path.endswith("/ingestions") and method == "POST":
        return "ingestion:*"

    return None