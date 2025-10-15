"""Multi-tenant filters for STAC API"""

import asyncio
import dataclasses
import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class AsyncTTLCache:
    """Async safe TTL cache"""

    ttl: int = 60
    max_size: int = 1000
    _cache: Dict[str, Tuple[Any, float, float]] = dataclasses.field(
        init=False, default_factory=dict
    )  # key -> (value, timestamp, access_time)
    _lock: asyncio.Lock = dataclasses.field(init=False, default_factory=asyncio.Lock)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp, _ = self._cache[key]
            current_time = time.time()

            # Check if value is expired
            if current_time - timestamp > self.ttl:
                del self._cache[key]
                return None

            self._cache[key] = (value, timestamp, current_time)
            return value

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL and LRU eviction"""
        async with self._lock:
            current_time = time.time()

            # If at max size, remove the least recently used item
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Find the least recently used item
                lru_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][2],  # access_time is second element
                )
                del self._cache[lru_key]

            self._cache[key] = (value, current_time, current_time)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> None:
        """Remove expired entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, timestamp, _) in self._cache.items()
                if current_time - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        async with self._lock:
            current_time = time.time()
            total_entries = len(self._cache)

            expired_entries = 0
            for entry in self._cache.values():
                _, timestamp, _ = entry
                if current_time - timestamp > self.ttl:
                    expired_entries += 1
            active_entries = total_entries - expired_entries

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
            }

    async def get_keys(self) -> list[str]:
        """Get all cache keys"""
        async with self._lock:
            return list(self._cache.keys())


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
    cache: AsyncTTLCache = dataclasses.field(init=False, default_factory=AsyncTTLCache)

    def __post_init__(self):
        """Initialize the ItemFilter"""
        self.client = httpx.AsyncClient(base_url=self.api_url)

    def configure_cache(self, ttl: int = 60, max_size: int = 1000) -> None:
        """Configure cache settings"""
        self.cache.ttl = ttl
        self.cache.max_size = max_size

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()

    async def clear_cache(self) -> None:
        """Clear the cache"""
        await self.cache.clear()

    async def get_cached_tenants(self) -> list[str]:
        """Get list of cached tenant keys"""
        return await self.cache.get_keys()

    async def __call__(self, context: dict[str, Any]) -> str:
        """If tenant is present on request, filter Items by Collection IDs available to that tenant"""
        logger.debug("calling ItemFilter with context %s", context)
        tenant = context.get("tenant")
        if not tenant:
            return "1=1"

        # Check cache first
        collection_ids = await self.cache.get(tenant)
        if collection_ids is None:
            collection_ids = await self.get_tenant_collections(tenant)
            await self.cache.set(tenant, collection_ids)

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
