"""
Test suite to test async-lru
"""

import pytest
from src.filters import ItemFilter


class TestItemFilterCache:
    """Test cases for ItemFilter with async-lru cache functionality"""

    @pytest.fixture
    def item_filter(self):
        """Create an ItemFilter for testing"""
        return ItemFilter(api_url="http://localhost:8081")

    @pytest.mark.asyncio
    async def test_cache_initialization(self, item_filter):
        """Test that cache is properly initialized and accessible"""
        assert callable(item_filter.get_tenant_collections)

        assert hasattr(item_filter.get_tenant_collections, "cache_info")
        cache_info = item_filter.get_tenant_collections.cache_info()
        assert hasattr(cache_info, "hits")
        assert hasattr(cache_info, "misses")
        assert hasattr(cache_info, "maxsize")
        assert hasattr(cache_info, "currsize")

    @pytest.mark.asyncio
    async def test_cache_stats(self, item_filter):
        """Test cache statistics and initial state"""
        stats = await item_filter.get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "maxsize" in stats
        assert "currsize" in stats

        # Initially empty cache
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["currsize"] == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, item_filter):
        """Test clearing the cache"""
        # Clear cache
        await item_filter.clear_cache()

        # Check that cache is cleared
        stats = await item_filter.get_cache_stats()
        assert stats["currsize"] == 0
