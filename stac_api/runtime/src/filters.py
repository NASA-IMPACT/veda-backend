"""Multi-tenant filters for STAC API"""

import dataclasses
import logging
from typing import Any, Optional

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

        # TODO: Figure out cause of "PostgresSyntaxError: syntax error at or near \"IN\"" /cc @bitnerd
        # return {
        #     "op": "in",
        #     "args": [{"property": "collection"}, collection_ids],
        # }

        return " OR ".join(
            f"collection = '{collection_id}'" for collection_id in collection_ids
        )

    # TODO: Memoize this with expiration
    async def get_tenant_collections(self, tenant: str) -> list[str]:
        """Fetch IDs of collections visible to a tenant"""
        logger.debug(
            "fetching tenant collections from %s for tenant %s",
            self.api_url,
            tenant,
        )
        ids = []

        url: Optional[str] = f"{self.api_url}/{tenant}/collections"
        while url:
            # TODO: Can we do this without going through HTTP?
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            ids.extend([collection["id"] for collection in data["collections"]])

            url = next(
                (link["href"] for link in data["links"] if link["rel"] == "next"),
                None,
            )

        return ids
