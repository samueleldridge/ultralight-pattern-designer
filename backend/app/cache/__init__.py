"""
Cache module - Redis connection and re-exports.
"""
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# Create Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis():
    """Get Redis connection"""
    return redis_client


# Re-export from enhanced module
from app.cache.enhanced import (
    EnhancedQueryCache,
    CacheKeyBuilder,
    CacheStrategy,
    CacheWarmer,
    CacheInvalidator,
    get_enhanced_cache,
    cached_query,
)

__all__ = [
    "redis_client",
    "get_redis",
    "EnhancedQueryCache",
    "CacheKeyBuilder",
    "CacheStrategy",
    "CacheWarmer",
    "CacheInvalidator",
    "get_enhanced_cache",
    "cached_query",
]
