"""Multi-tenant filters for STAC API"""

import dataclasses
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CollectionFilter:
    """Tooling to filter STAC Collections by tenant"""

    async def __call__(self, context: dict[str, Any]) -> str:
        """If tenant is present on request, filter Collections by that tenant"""
        logger.debug("calling CollectionFilter with context %s", context)
        tenant = context.get("tenant")
        if tenant:
            return f"dashboard:tenant = '{tenant}'"
        return "1=1"


@dataclasses.dataclass
class ItemFilter:
    """Tooling to filter STAC Items by tenant"""

    api_url: str

    def __post_init__(self):
        """Initialize the ItemFilter"""
        self.client = httpx.AsyncClient(base_url=self.api_url)

    async def __call__(self, context: dict[str, Any]) -> str:
        """If tenant is present on request, filter Items by Collection IDs available to that tenant"""
        logger.debug("calling ItemFilter with context %s", context)
        tenant = context.get("tenant")
        if not tenant:
            return "1=1"

        collection_ids = await self.get_tenant_collections(tenant)
        if not collection_ids:
            logger.debug("No collections found for tenant %s", tenant)
            return "1=0"

        # HACK: To avoid SQL issues, we're just filtering on the first collection for now
        return f"collection = '{collection_ids[0]}'"
        # TODO: Figure out cause of "PostgresSyntaxError: syntax error at or near \"IN\"" /cc @bitnerd
        return {
            "op": "in",
            "args": [{"property": "collection"}, collection_ids],
        }

    # TODO: Memoize this with expiration
    async def get_tenant_collections(self, tenant: str) -> list[str]:
        """Fetch IDs of collections visible to a tenant"""
        logger.debug(
            "fetching tenant collections from %s for tenant %s",
            self.api_url,
            tenant,
        )
        # TODO: Can we do this without going through HTTP?
        response = await self.client.get(f"{self.api_url}/{tenant}/collections")
        response.raise_for_status()
        data = response.json()

        ids = [collection["id"] for collection in data["collections"]]
        # TODO: support pagination
        return ids
