"""
Test suite for AsyncTTLCache
"""

import asyncio
import pytest
import time
from src.filters import AsyncTTLCache, ItemFilter


class TestAsyncTTLCache:
    """Test cases for AsyncTTLCache functionality"""

    @pytest.fixture
    def cache(self):
        """Create a test cache with short TTL for testing"""
        return AsyncTTLCache(ttl=2, max_size=3)

    @pytest.mark.asyncio
    async def test_basic_set_get(self, cache):
        """Test basic set and get operations"""
        await cache.set("tenant1", ["collection1", "collection2"])
        result = await cache.get("tenant1")
        assert result == ["collection1", "collection2"]

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss returns None"""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test that values expire after TTL"""
        await cache.set("tenant1", ["collection1"])

        result = await cache.get("tenant1")
        assert result == ["collection1"]

        # wait for expiration and then check cache
        await asyncio.sleep(2.1)
        result = await cache.get("tenant1")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when cache is full"""
        # Fill cache to max size
        await cache.set("tenant1", ["col1"])
        await cache.set("tenant2", ["col2"])
        await cache.set("tenant3", ["col3"])

        # Access tenant1 to make it recently used
        await cache.get("tenant1")

        # Add new tenant (should evict tenant2, not tenant1)
        await cache.set("tenant4", ["col4"])

        # Check what's still in cache
        assert await cache.get("tenant1") == ["col1"]  # Should exist
        assert await cache.get("tenant2") is None      # Should be evicted
        assert await cache.get("tenant3") == ["col3"]  # Should exist
        assert await cache.get("tenant4") == ["col4"]  # Should exist

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """Test cache statistics"""
        # Initially empty
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0

        # Add some entries
        await cache.set("tenant1", ["col1"])
        await cache.set("tenant2", ["col2"])

        stats = await cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["max_size"] == 3
        assert stats["ttl_seconds"] == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        """Test manual cleanup of expired entries"""
        # Add entries
        await cache.set("tenant1", ["col1"])
        await cache.set("tenant2", ["col2"])

        # Wait for expiration
        await asyncio.sleep(2.1)

        # Manually cleanup
        await cache.cleanup_expired()

        # All should be gone
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, cache):
        """Test clearing the cache"""
        # Add entries
        await cache.set("tenant1", ["col1"])
        await cache.set("tenant2", ["col2"])

        # Clear cache
        await cache.clear()

        # Should be empty
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_performance(self, cache):
        """Test cache performance characteristics"""
        # Test set performance
        start_time = time.time()
        for i in range(1000):
            await cache.set(f"tenant{i}", [f"collection{i}"])
        set_time = time.time() - start_time

        # Test get performance
        start_time = time.time()
        for i in range(1000):
            await cache.get(f"tenant{i}")
        get_time = time.time() - start_time

        assert set_time < 1.0
        assert get_time < 1.0


class TestItemFilterCache:
    """Test cases for ItemFilter with cache functionality"""

    @pytest.fixture
    def item_filter(self):
        """Create an ItemFilter for testing"""
        return ItemFilter(api_url="http://localhost:8081")

    @pytest.mark.asyncio
    async def test_cache_configuration(self, item_filter):
        """Test cache configuration"""
        item_filter.configure_cache(ttl=30, max_size=50)

        stats = await item_filter.get_cache_stats()
        assert stats["ttl_seconds"] == 30
        assert stats["max_size"] == 50

    @pytest.mark.asyncio
    async def test_cache_operations(self, item_filter):
        """Test cache operations on ItemFilter"""
        stats = await item_filter.get_cache_stats()
        assert stats["total_entries"] == 0

        await item_filter.clear_cache()

        # check that the cache is still empty
        stats = await item_filter.get_cache_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_cached_tenants(self, item_filter):
        """Test getting cached tenant keys"""
        # Initially no cached tenants
        tenants = await item_filter.get_cached_tenants()
        assert len(tenants) == 0