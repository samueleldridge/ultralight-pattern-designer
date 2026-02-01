import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# Create Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis():
    """Get Redis connection"""
    return redis_client
