"""
Enhanced caching layer with Redis.
Includes query result caching, cache warming, and intelligent invalidation.
"""

import json
import hashlib
import asyncio
from typing import Optional, Dict, Any, List, Callable, Set
from datetime import datetime, timedelta
from functools import wraps
import redis.asyncio as redis
from app.config import get_settings


class CacheKeyBuilder:
    """Build cache keys from various inputs"""
    
    @staticmethod
    def from_sql(query: str, params: Optional[Dict] = None, dialect: str = "") -> str:
        """Generate cache key from SQL query and parameters"""
        # Normalize query
        normalized = query.strip().lower()
        normalized = " ".join(normalized.split())  # Remove extra whitespace
        
        # Create key components
        components = [dialect, normalized]
        if params:
            # Sort params for consistent ordering
            param_str = json.dumps(params, sort_keys=True)
            components.append(param_str)
        
        # Hash the combined components
        key_data = "|".join(components)
        return f"sql:{hashlib.sha256(key_data.encode()).hexdigest()}"
    
    @staticmethod
    def from_user_context(
        query: str,
        user_id: str,
        tenant_id: str,
        connection_id: str
    ) -> str:
        """Generate cache key including user context"""
        components = [
            user_id,
            tenant_id,
            connection_id,
            query.strip().lower()
        ]
        key_data = "|".join(components)
        return f"ctx:{hashlib.sha256(key_data.encode()).hexdigest()}"
    
    @staticmethod
    def from_endpoint(endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for API endpoint"""
        components = [endpoint]
        if params:
            param_str = json.dumps(params, sort_keys=True)
            components.append(param_str)
        
        key_data = "|".join(components)
        return f"api:{hashlib.sha256(key_data.encode()).hexdigest()}"


class CacheStrategy:
    """Define cache behavior strategies"""
    
    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_size_mb: float = 10.0,
        compress: bool = True,
        invalidate_on: Optional[List[str]] = None,
        warm_on_startup: bool = False
    ):
        self.ttl_seconds = ttl_seconds
        self.max_size_mb = max_size_mb
        self.compress = compress
        self.invalidate_on = invalidate_on or []
        self.warm_on_startup = warm_on_startup


class EnhancedQueryCache:
    """
    Enhanced caching with compression, serialization, and invalidation.
    """
    
    # Common non-cacheable SQL functions
    NON_CACHEABLE_FUNCTIONS = [
        'NOW()', 'CURRENT_DATE', 'CURRENT_TIMESTAMP',
        'CURRENT_TIME', 'LOCALTIME', 'LOCALTIMESTAMP',
        'RAND()', 'RANDOM()', 'UUID()', 'NEWID()',
        'SYSDATE', 'GETDATE()', 'SYSTIMESTAMP'
    ]
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._key_builder = CacheKeyBuilder()
        self._local_cache: Dict[str, Any] = {}
        self._local_cache_ttl: Dict[str, float] = {}
        self._local_cache_max_size = 1000
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            from app.cache import get_redis
            self._redis = await get_redis()
        return self._redis
    
    def _is_cacheable(self, query: str) -> bool:
        """Check if query should be cached"""
        query_upper = query.upper()
        
        # Check for non-cacheable functions
        for func in self.NON_CACHEABLE_FUNCTIONS:
            if func.upper() in query_upper:
                return False
        
        # Check for temp tables or volatile operations
        if any(kw in query_upper for kw in ['TEMPORARY', 'TEMP', 'CREATE TABLE']):
            return False
        
        return True
    
    def _serialize(self, data: Any) -> str:
        """Serialize data with optional compression"""
        json_str = json.dumps(data, default=str)
        return json_str
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize cached data"""
        return json.loads(data)
    
    async def get(
        self,
        key: str,
        use_local: bool = True
    ) -> Optional[Any]:
        """Get value from cache"""
        # Check local cache first
        if use_local and key in self._local_cache:
            if time.time() < self._local_cache_ttl.get(key, 0):
                return self._local_cache[key]
            else:
                # Expired
                del self._local_cache[key]
                del self._local_cache_ttl[key]
        
        # Check Redis
        redis_client = await self._get_redis()
        cached = await redis_client.get(key)
        
        if cached:
            data = self._deserialize(cached)
            
            # Update local cache
            if use_local:
                self._update_local_cache(key, data)
            
            return data
        
        return None
    
    def _update_local_cache(self, key: str, data: Any):
        """Update local LRU cache"""
        # Simple eviction if at capacity
        if len(self._local_cache) >= self._local_cache_max_size:
            # Remove oldest entry (simplified)
            oldest_key = next(iter(self._local_cache))
            del self._local_cache[oldest_key]
            if oldest_key in self._local_cache_ttl:
                del self._local_cache_ttl[oldest_key]
        
        self._local_cache[key] = data
        self._local_cache_ttl[key] = time.time() + 60  # 1 minute local TTL
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        update_local: bool = True
    ):
        """Set value in cache"""
        # Serialize
        serialized = self._serialize(value)
        
        # Check size
        size_mb = len(serialized.encode()) / (1024 * 1024)
        if size_mb > 10:  # Max 10MB
            return  # Don't cache very large results
        
        # Set in Redis
        redis_client = await self._get_redis()
        await redis_client.setex(key, ttl_seconds, serialized)
        
        # Update local cache
        if update_local:
            self._update_local_cache(key, value)
    
    async def delete(self, key: str):
        """Delete from cache"""
        # Remove from local
        if key in self._local_cache:
            del self._local_cache[key]
            del self._local_cache_ttl[key]
        
        # Remove from Redis
        redis_client = await self._get_redis()
        await redis_client.delete(key)
    
    async def get_query_result(
        self,
        query: str,
        connection_id: str,
        params: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get cached query result"""
        if not self._is_cacheable(query):
            return None
        
        if user_id:
            key = self._key_builder.from_user_context(
                query, user_id, "", connection_id
            )
        else:
            key = self._key_builder.from_sql(query, params, connection_id)
        
        cached = await self.get(key)
        
        if cached:
            return {
                **cached,
                "from_cache": True,
                "cache_key": key
            }
        
        return None
    
    async def set_query_result(
        self,
        query: str,
        connection_id: str,
        result: Dict,
        params: Optional[Dict] = None,
        user_id: Optional[str] = None,
        ttl_seconds: int = 3600
    ):
        """Cache query result"""
        if not self._is_cacheable(query):
            return
        
        if user_id:
            key = self._key_builder.from_user_context(
                query, user_id, "", connection_id
            )
        else:
            key = self._key_builder.from_sql(query, params, connection_id)
        
        cache_data = {
            "result": result,
            "cached_at": datetime.utcnow().isoformat(),
            "query_preview": query[:200]
        }
        
        await self.set(key, cache_data, ttl_seconds)
    
    async def invalidate_connection(self, connection_id: str):
        """Invalidate all cached queries for a connection"""
        redis_client = await self._get_redis()
        
        # Find all keys for this connection
        pattern = f"*{connection_id}*"
        cursor = 0
        
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            
            if cursor == 0:
                break
        
        # Also clear local cache
        keys_to_remove = [
            k for k in self._local_cache 
            if connection_id in k
        ]
        for key in keys_to_remove:
            del self._local_cache[key]
            if key in self._local_cache_ttl:
                del self._local_cache_ttl[key]
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache by pattern"""
        redis_client = await self._get_redis()
        
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            
            if cursor == 0:
                break


class CacheWarmer:
    """
    Pre-populate cache with common queries.
    """
    
    def __init__(self, cache: EnhancedQueryCache):
        self.cache = cache
        self._warm_queries: List[Dict] = []
    
    def register_query(
        self,
        name: str,
        query_func: Callable,
        params: Optional[Dict] = None,
        schedule: Optional[str] = None  # cron-like schedule
    ):
        """Register a query to be warmed"""
        self._warm_queries.append({
            "name": name,
            "query_func": query_func,
            "params": params or {},
            "schedule": schedule
        })
    
    async def warm_all(self):
        """Execute all registered warm queries"""
        results = []
        
        for query_def in self._warm_queries:
            try:
                start_time = time.time()
                result = await query_def["query_func"](**query_def["params"])
                duration = time.time() - start_time
                
                results.append({
                    "name": query_def["name"],
                    "status": "success",
                    "duration": duration
                })
            except Exception as e:
                results.append({
                    "name": query_def["name"],
                    "status": "error",
                    "error": str(e)
                })
        
        return results


class CacheInvalidator:
    """
    Manage cache invalidation strategies.
    """
    
    def __init__(self, cache: EnhancedQueryCache):
        self.cache = cache
        self._invalidation_rules: Dict[str, List[str]] = {}
    
    def register_invalidation(
        self,
        table_name: str,
        cache_patterns: List[str]
    ):
        """
        Register cache patterns to invalidate when table changes.
        """
        if table_name not in self._invalidation_rules:
            self._invalidation_rules[table_name] = []
        
        self._invalidation_rules[table_name].extend(cache_patterns)
    
    async def invalidate_for_table(self, table_name: str):
        """Invalidate cache entries affected by table changes"""
        patterns = self._invalidation_rules.get(table_name, [])
        
        for pattern in patterns:
            await self.cache.invalidate_pattern(pattern)


# Import at end to avoid circular imports
import time

# Global cache instance
_cache_instance: Optional[EnhancedQueryCache] = None


def get_enhanced_cache() -> EnhancedQueryCache:
    """Get global enhanced cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = EnhancedQueryCache()
    return _cache_instance


async def cached_query(
    query: str,
    connection_id: str,
    execute_func: Callable,
    params: Optional[Dict] = None,
    user_id: Optional[str] = None,
    ttl_seconds: int = 3600,
    use_cache: bool = True
):
    """
    Execute query with caching.
    """
    cache = get_enhanced_cache()
    
    # Try cache first
    if use_cache:
        cached = await cache.get_query_result(
            query, connection_id, params, user_id
        )
        if cached:
            return cached["result"]
    
    # Execute
    result = await execute_func()
    
    # Cache result
    if use_cache:
        await cache.set_query_result(
            query, connection_id, result, params, user_id, ttl_seconds
        )
    
    return result
