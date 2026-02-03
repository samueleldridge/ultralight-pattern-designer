"""
Cache Abstraction Layer

Provides unified caching interface with Redis as primary and SQLite as fallback.
Automatically handles Redis unavailability gracefully.

Usage:
    from app.cache import get_cache
    
    cache = await get_cache()
    await cache.set("key", "value", ttl=3600)
    value = await cache.get("key")
"""

import json
import sqlite3
import asyncio
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class RedisCache(CacheBackend):
    """Redis cache backend"""
    
    def __init__(self, redis_client):
        self._redis = redis_client
    
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._redis.get(key)
        except Exception:
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        try:
            if ttl:
                await self._redis.setex(key, ttl, value)
            else:
                await self._redis.set(key, value)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            await self._redis.delete(key)
            return True
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        try:
            return await self._redis.exists(key) > 0
        except Exception:
            return False


class SQLiteCache(CacheBackend):
    """SQLite cache backend for when Redis is unavailable"""
    
    def __init__(self, db_path: str = "./cache.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def _init_db(self):
        """Initialize SQLite cache table"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            def _create_table():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)
                """)
                conn.commit()
                conn.close()
            
            await asyncio.get_event_loop().run_in_executor(None, _create_table)
            self._initialized = True
    
    async def get(self, key: str) -> Optional[str]:
        await self._init_db()
        
        def _get():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                (key, datetime.utcnow())
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        await self._init_db()
        
        def _set():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expires_at)
                VALUES (?, ?, ?)
                """,
                (key, value, expires_at)
            )
            conn.commit()
            conn.close()
            return True
        
        return await asyncio.get_event_loop().run_in_executor(None, _set)
    
    async def delete(self, key: str) -> bool:
        await self._init_db()
        
        def _delete():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return True
        
        return await asyncio.get_event_loop().run_in_executor(None, _delete)
    
    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None
    
    async def cleanup(self):
        """Remove expired entries"""
        await self._init_db()
        
        def _cleanup():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.utcnow(),)
            )
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(None, _cleanup)


class MemoryCache(CacheBackend):
    """In-memory cache for testing/single-process use"""
    
    def __init__(self):
        self._data: Dict[str, tuple[str, Optional[datetime]]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key not in self._data:
                return None
            
            value, expires_at = self._data[key]
            if expires_at and datetime.utcnow() > expires_at:
                del self._data[key]
                return None
            
            return value
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            self._data[key] = (value, expires_at)
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None


class CacheManager:
    """Manages cache backends with automatic fallback"""
    
    def __init__(self):
        self._redis: Optional[RedisCache] = None
        self._sqlite: Optional[SQLiteCache] = None
        self._memory: Optional[MemoryCache] = None
        self._primary: Optional[CacheBackend] = None
        self._redis_available: bool = False
    
    async def initialize(self):
        """Initialize cache with Redis if available, fallback to SQLite"""
        # Try Redis first
        try:
            from app.config import get_settings
            settings = get_settings()
            
            import redis.asyncio as redis_lib
            client = redis_lib.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            
            # Test connection
            await client.ping()
            
            self._redis = RedisCache(client)
            self._primary = self._redis
            self._redis_available = True
            print("✅ Cache: Using Redis")
            
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}")
            print("✅ Cache: Using SQLite fallback")
            
            # Fall back to SQLite
            self._sqlite = SQLiteCache("./cache.db")
            self._primary = self._sqlite
            self._redis_available = False
    
    @property
    def is_redis_available(self) -> bool:
        return self._redis_available
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if self._primary is None:
            await self.initialize()
        return await self._primary.get(key)
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if self._primary is None:
            await self.initialize()
        return await self._primary.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if self._primary is None:
            await self.initialize()
        return await self._primary.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if self._primary is None:
            await self.initialize()
        return await self._primary.exists(key)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache() -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    return _cache_manager


# Legacy compatibility - redirect to new cache manager
async def get_redis():
    """Legacy function - returns cache manager that acts like Redis"""
    cache = await get_cache()
    # Return a wrapper that mimics Redis interface
    return _RedisWrapper(cache)


class _RedisWrapper:
    """Wraps CacheManager to provide Redis-like interface for legacy code"""
    
    def __init__(self, cache: CacheManager):
        self._cache = cache
    
    async def get(self, key: str) -> Optional[str]:
        return await self._cache.get(key)
    
    async def set(self, key: str, value: str) -> bool:
        return await self._cache.set(key, value)
    
    async def setex(self, key: str, ttl: int, value: str) -> bool:
        return await self._cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        return await self._cache.delete(key)
    
    async def exists(self, key: str) -> int:
        return 1 if await self._cache.exists(key) else 0
    
    async def ping(self):
        """Always returns True (compatibility)"""
        return True


# Re-export from enhanced module (with fallback handling)
from app.cache.enhanced import (
    CacheKeyBuilder,
    CacheStrategy,
    CacheWarmer,
    CacheInvalidator,
    cached_query,
)


# Legacy compatibility shim for code that imports get_enhanced_cache
class _EnhancedCacheShim:
    """Shim that provides get_enhanced_cache interface"""
    
    def __init__(self):
        self._cache = None
    
    async def _get_redis(self):
        """Return cache wrapper that mimics Redis interface"""
        cache = await get_cache()
        return _RedisWrapper(cache)
    
    async def get(self, key: str) -> Optional[str]:
        cache = await get_cache()
        return await cache.get(key)
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        cache = await get_cache()
        return await cache.set(key, value, ttl)


# Legacy singleton
_enhanced_cache_shim = None


async def get_enhanced_cache():
    """Legacy function - returns cache shim with Redis-like interface"""
    global _enhanced_cache_shim
    if _enhanced_cache_shim is None:
        _enhanced_cache_shim = _EnhancedCacheShim()
    return _enhanced_cache_shim

__all__ = [
    "get_cache",
    "get_redis",  # Legacy
    "get_enhanced_cache",  # Legacy
    "CacheManager",
    "CacheBackend",
    "RedisCache",
    "SQLiteCache",
    "MemoryCache",
    "CacheKeyBuilder",
    "CacheStrategy",
    "CacheWarmer",
    "CacheInvalidator",
    "cached_query",
]
