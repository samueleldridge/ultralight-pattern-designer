"""
Middleware module initialization.
Exports all middleware classes and functions.
"""

from .rate_limiting import (
    RateLimitMiddleware,
    RateLimiter,
    RateLimitExceeded,
    query_rate_limiter,
    export_rate_limiter,
    webhook_rate_limiter,
    check_rate_limit,
)

from .timeouts import (
    QueryLimitsMiddleware,
    QueryTimeoutManager,
    QueryLimitExceeded,
    QueryLimits,
    QueryComplexityAnalyzer,
    enforce_query_limits,
    add_query_limits,
    STRICT_LIMITS,
    DEFAULT_LIMITS,
    RELAXED_LIMITS,
)

from .auth import (
    AuthMiddleware,
    TenantMiddleware,
    ClerkAuth,
    PermissionChecker,
    AuthenticationError,
    AuthorizationError,
    get_current_user,
    require_auth,
    require_permission,
)

__all__ = [
    # Rate Limiting
    "RateLimitMiddleware",
    "RateLimiter",
    "RateLimitExceeded",
    "query_rate_limiter",
    "export_rate_limiter",
    "webhook_rate_limiter",
    "check_rate_limit",
    
    # Timeouts & Limits
    "QueryLimitsMiddleware",
    "QueryTimeoutManager",
    "QueryLimitExceeded",
    "QueryLimits",
    "QueryComplexityAnalyzer",
    "enforce_query_limits",
    "add_query_limits",
    "STRICT_LIMITS",
    "DEFAULT_LIMITS",
    "RELAXED_LIMITS",
    
    # Auth
    "AuthMiddleware",
    "TenantMiddleware",
    "ClerkAuth",
    "PermissionChecker",
    "AuthenticationError",
    "AuthorizationError",
    "get_current_user",
    "require_auth",
    "require_permission",
]
