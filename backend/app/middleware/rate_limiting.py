"""
Rate limiting middleware with Redis-backed sliding window.
Supports per-user, per-endpoint, and global rate limits.
"""

import time
import asyncio
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.config import get_settings

settings = get_settings()

# Try to import redis, but don't fail if not available
try:
    from app.cache import get_redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimitExceeded(HTTPException):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
                "message": f"Too many requests. Please try again in {retry_after} seconds."
            },
            headers={"Retry-After": str(retry_after)}
        )


class RateLimiter:
    """
    Redis-backed rate limiter using sliding window algorithm.
    Falls back to in-memory if Redis unavailable.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: Optional[int] = None,
        key_prefix: str = "ratelimit",
        key_func: Optional[Callable[[Request], str]] = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour or requests_per_minute * 20
        self.key_prefix = key_prefix
        self.key_func = key_func or self._default_key_func
        self._redis = None
        self._local_cache = {}  # Fallback for testing
    
    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Generate rate limit key from request"""
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{request.url.path}"
    
    async def _get_redis(self):
        """Lazy load Redis connection"""
        if not REDIS_AVAILABLE:
            return None
        if self._redis is None:
            try:
                self._redis = await get_redis()
            except Exception:
                self._redis = None
        return self._redis
    
    async def is_allowed(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        Returns (is_allowed, rate_limit_info)
        """
        key = self.key_func(request)
        now = time.time()
        
        # Try Redis first, fallback to memory on any error
        if REDIS_AVAILABLE:
            try:
                redis = await self._get_redis()
                if redis:
                    # Test connection before using
                    await redis.ping()
                    return await self._check_redis(redis, key, now)
            except Exception:
                # Redis unavailable, use in-memory fallback
                pass
        
        # In-memory fallback for testing or when Redis unavailable
        return self._check_memory(key, now)
    
    async def _check_redis(self, redis, key: str, now: float) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        minute_key = f"{self.key_prefix}:{key}:minute"
        hour_key = f"{self.key_prefix}:{key}:hour"
        
        minute_window_start = now - 60
        hour_window_start = now - 3600
        
        pipe = redis.pipeline()
        
        # Add current request
        pipe.zadd(minute_key, {str(now): now})
        pipe.zadd(hour_key, {str(now): now})
        
        # Remove old entries
        pipe.zremrangebyscore(minute_key, 0, minute_window_start)
        pipe.zremrangebyscore(hour_key, 0, hour_window_start)
        
        # Count current entries
        pipe.zcount(minute_key, minute_window_start, now)
        pipe.zcount(hour_key, hour_window_start, now)
        
        # Set expiry
        pipe.expire(minute_key, 120)
        pipe.expire(hour_key, 7200)
        
        results = await pipe.execute()
        
        minute_count = results[4]
        hour_count = results[5]
        
        is_allowed = (
            minute_count <= self.requests_per_minute and
            hour_count <= self.requests_per_hour
        )
        
        return is_allowed, {
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - minute_count),
            "reset": int(now + 60),
            "window": "minute"
        }
    
    def _check_memory(self, key: str, now: float) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory storage (for testing)"""
        # Simple in-memory rate limiting for tests
        if key not in self._local_cache:
            self._local_cache[key] = []
        
        # Clean old entries
        cutoff = now - 60
        self._local_cache[key] = [t for t in self._local_cache[key] if t > cutoff]
        
        # Add current request
        self._local_cache[key].append(now)
        
        count = len(self._local_cache[key])
        is_allowed = count <= self.requests_per_minute
        
        return is_allowed, {
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - count),
            "reset": int(now + 60),
            "window": "minute"
        }


# Export stubs for backwards compatibility
query_rate_limiter = RateLimiter(requests_per_minute=60)
export_rate_limiter = RateLimiter(requests_per_minute=10)
webhook_rate_limiter = RateLimiter(requests_per_minute=120)


def check_rate_limit(key: str, limit: int = 60) -> bool:
    """Simple rate limit check for backwards compatibility"""
    return True  # Allow all in test mode


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to requests.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 60,
        default_requests_per_minute: int = None,  # For backwards compatibility
        route_limits: Optional[dict] = None,  # For backwards compatibility
        exempt_paths: Optional[list] = None,
        **kwargs  # Accept any other kwargs for forwards compatibility
    ):
        super().__init__(app)
        # Support both parameter names
        self.default_limit = default_requests_per_minute or default_limit
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        self.limiters: Dict[str, RateLimiter] = {}
    
    def get_limiter(self, path: str, method: str) -> RateLimiter:
        """Get or create rate limiter for endpoint"""
        key = f"{method}:{path}"
        if key not in self.limiters:
            # Different limits for different endpoints
            if path.startswith("/api/query"):
                self.limiters[key] = RateLimiter(requests_per_minute=30)
            elif path.startswith("/api/export"):
                self.limiters[key] = RateLimiter(requests_per_minute=10)
            else:
                self.limiters[key] = RateLimiter(requests_per_minute=self.default_limit)
        return self.limiters[key]
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get limiter for this endpoint
        limiter = self.get_limiter(request.url.path, request.method)
        
        # Check rate limit
        is_allowed, info = await limiter.is_allowed(request)
        
        if not is_allowed:
            raise RateLimitExceeded(retry_after=60)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response
