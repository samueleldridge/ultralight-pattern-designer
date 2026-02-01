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
from app.cache import get_redis
from app.config import get_settings


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
    
    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Generate rate limit key from request"""
        # Use user ID if authenticated, otherwise IP + user agent hash
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP + path
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def _get_redis(self):
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def is_allowed(
        self, 
        request: Request,
        resource: Optional[str] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        Returns (is_allowed, rate_limit_info)
        """
        key = self.key_func(request)
        resource_key = resource or request.url.path
        
        redis = await self._get_redis()
        now = time.time()
        
        # Per-minute window
        minute_key = f"{self.key_prefix}:{key}:{resource_key}:minute"
        hour_key = f"{self.key_prefix}:{key}:{resource_key}:hour"
        
        # Check per-minute limit
        minute_window_start = now - 60
        minute_count = await redis.zcount(minute_key, minute_window_start, now)
        
        # Check per-hour limit
        hour_window_start = now - 3600
        hour_count = await redis.zcount(hour_key, hour_window_start, now)
        
        info = {
            "limit_per_minute": self.requests_per_minute,
            "limit_per_hour": self.requests_per_hour,
            "remaining_per_minute": max(0, self.requests_per_minute - minute_count - 1),
            "remaining_per_hour": max(0, self.requests_per_hour - hour_count - 1),
            "reset_time": int(now + 60)
        }
        
        if minute_count >= self.requests_per_minute:
            # Find when the oldest request in window will expire
            oldest = await redis.zrange(minute_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + 60 - now)
                return False, {**info, "retry_after": max(1, retry_after)}
            return False, {**info, "retry_after": 60}
        
        if hour_count >= self.requests_per_hour:
            oldest = await redis.zrange(hour_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + 3600 - now)
                return False, {**info, "retry_after": max(1, retry_after)}
            return False, {**info, "retry_after": 3600}
        
        return True, info
    
    async def record_request(
        self, 
        request: Request,
        resource: Optional[str] = None
    ):
        """Record a request in the rate limit counters"""
        key = self.key_func(request)
        resource_key = resource or request.url.path
        
        redis = await self._get_redis()
        now = time.time()
        
        minute_key = f"{self.key_prefix}:{key}:{resource_key}:minute"
        hour_key = f"{self.key_prefix}:{key}:{resource_key}:hour"
        
        # Add current request to both windows
        pipe = redis.pipeline()
        pipe.zadd(minute_key, {str(now): now})
        pipe.zadd(hour_key, {str(now): now})
        
        # Remove old entries and set expiry
        pipe.zremrangebyscore(minute_key, 0, now - 60)
        pipe.zremrangebyscore(hour_key, 0, now - 3600)
        
        pipe.expire(minute_key, 120)  # 2 minutes
        pipe.expire(hour_key, 7200)   # 2 hours
        
        await pipe.execute()
    
    async def get_current_usage(self, request: Request) -> Dict[str, Any]:
        """Get current rate limit usage for requester"""
        key = self.key_func(request)
        redis = await self._get_redis()
        now = time.time()
        
        # Get all keys for this user
        pattern = f"{self.key_prefix}:{key}:*:minute"
        keys = await redis.keys(pattern)
        
        total_minute = 0
        for k in keys:
            count = await redis.zcount(k, now - 60, now)
            total_minute += count
        
        return {
            "requests_last_minute": total_minute,
            "limit_per_minute": self.requests_per_minute,
            "requests_last_hour": 0,  # Simplified for now
            "limit_per_hour": self.requests_per_hour
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    Configurable per-route limits.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_requests_per_minute: int = 60,
        default_requests_per_hour: Optional[int] = None,
        exempt_routes: Optional[list] = None,
        route_limits: Optional[Dict[str, Dict]] = None
    ):
        super().__init__(app)
        self.default_limiter = RateLimiter(
            requests_per_minute=default_requests_per_minute,
            requests_per_hour=default_requests_per_hour
        )
        self.exempt_routes = exempt_routes or ["/health", "/docs", "/openapi.json"]
        self.route_limits = route_limits or {}
        self._limiter_cache: Dict[str, RateLimiter] = {}
    
    def _get_limiter_for_route(self, path: str) -> RateLimiter:
        """Get rate limiter for specific route"""
        if path in self._limiter_cache:
            return self._limiter_cache[path]
        
        if path in self.route_limits:
            config = self.route_limits[path]
            limiter = RateLimiter(
                requests_per_minute=config.get("rpm", 60),
                requests_per_hour=config.get("rph")
            )
            self._limiter_cache[path] = limiter
            return limiter
        
        return self.default_limiter
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt routes
        if any(request.url.path.startswith(route) for route in self.exempt_routes):
            response = await call_next(request)
            return response
        
        limiter = self._get_limiter_for_route(request.url.path)
        
        # Check if allowed
        is_allowed, info = await limiter.is_allowed(request)
        
        if not is_allowed:
            raise RateLimitExceeded(retry_after=info.get("retry_after", 60))
        
        # Record the request
        await limiter.record_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit_per_minute"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining_per_minute"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
        
        return response


# Pre-configured rate limiters for common use cases
query_rate_limiter = RateLimiter(
    requests_per_minute=30,  # Queries are expensive
    requests_per_hour=500
)

export_rate_limiter = RateLimiter(
    requests_per_minute=5,   # Exports are very expensive
    requests_per_hour=50
)

webhook_rate_limiter = RateLimiter(
    requests_per_minute=100,  # Webhooks can be higher
    requests_per_hour=5000
)


async def check_rate_limit(
    request: Request,
    limiter: RateLimiter,
    resource: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check rate limit for a specific request.
    Raises RateLimitExceeded if over limit.
    """
    is_allowed, info = await limiter.is_allowed(request, resource)
    
    if not is_allowed:
        raise RateLimitExceeded(retry_after=info.get("retry_after", 60))
    
    await limiter.record_request(request, resource)
    return info
