"""
Error handling and recovery mechanisms.
Graceful failure handling with fallbacks.
"""

import asyncio
import random
from typing import Optional, TypeVar, Callable, Any, Dict, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ErrorCategory(Enum):
    """Categories of errors"""
    USER_ERROR = "user_error"          # User input error, bad query, etc.
    SYSTEM_ERROR = "system_error"      # Internal system error
    NETWORK_ERROR = "network_error"    # Network/connectivity issues
    DATABASE_ERROR = "database_error"  # Database errors
    LLM_ERROR = "llm_error"            # LLM API errors
    RATE_LIMIT_ERROR = "rate_limit"    # Rate limiting
    TIMEOUT_ERROR = "timeout"          # Timeout errors
    AUTH_ERROR = "auth_error"          # Authentication/authorization errors


@dataclass
class AppError:
    """Structured application error"""
    category: ErrorCategory
    message: str
    code: str
    details: Optional[Dict] = None
    retryable: bool = False
    retry_after_seconds: Optional[int] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "error": True,
            "category": self.category.value,
            "message": self.message,
            "code": self.code,
            "details": self.details,
            "retryable": self.retryable,
            "retry_after": self.retry_after_seconds,
            "suggestion": self.suggestion
        }


class ErrorClassifier:
    """Classify exceptions into error categories"""
    
    @staticmethod
    def classify(exception: Exception) -> AppError:
        """Classify an exception"""
        error_str = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Timeout errors
        if any(kw in error_str for kw in ['timeout', 'timed out']):
            return AppError(
                category=ErrorCategory.TIMEOUT_ERROR,
                message="Request timed out. Please try again.",
                code="TIMEOUT",
                retryable=True,
                retry_after_seconds=5,
                suggestion="Try simplifying your query or adding filters"
            )
        
        # Rate limit errors
        if any(kw in error_str for kw in ['rate limit', 'too many requests', '429']):
            return AppError(
                category=ErrorCategory.RATE_LIMIT_ERROR,
                message="Rate limit exceeded. Please slow down.",
                code="RATE_LIMITED",
                retryable=True,
                retry_after_seconds=60,
                suggestion="Wait a moment before making more requests"
            )
        
        # Database connection errors
        if any(kw in error_str for kw in ['connection', 'database', 'sql']):
            return AppError(
                category=ErrorCategory.DATABASE_ERROR,
                message="Database error occurred",
                code="DB_ERROR",
                retryable=True,
                retry_after_seconds=5,
                suggestion="Check your database connection and try again"
            )
        
        # LLM errors
        if any(kw in error_str for kw in ['llm', 'openai', 'moonshot', 'kimi', 'gpt']):
            return AppError(
                category=ErrorCategory.LLM_ERROR,
                message="AI service temporarily unavailable",
                code="LLM_ERROR",
                retryable=True,
                retry_after_seconds=10,
                suggestion="The AI service is experiencing issues. Retrying..."
            )
        
        # Auth errors
        if any(kw in error_str for kw in ['auth', 'unauthorized', 'forbidden', 'permission']):
            return AppError(
                category=ErrorCategory.AUTH_ERROR,
                message="Authentication failed",
                code="AUTH_ERROR",
                retryable=False,
                suggestion="Please log in again"
            )
        
        # Default to system error
        return AppError(
            category=ErrorCategory.SYSTEM_ERROR,
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
            retryable=True,
            retry_after_seconds=5,
            suggestion="Please try again or contact support"
        )


T = TypeVar('T')


class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[tuple] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError
        )


class RetryHandler:
    """Handle retries with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add random jitter (±25%)
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter
        
        return delay
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not isinstance(e, self.config.retryable_exceptions):
                    raise
                
                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception


class DatabaseConnectionRetry:
    """
    Database connection with automatic retry.
    """
    
    def __init__(
        self,
        connection_factory: Callable,
        retry_config: Optional[RetryConfig] = None
    ):
        self.connection_factory = connection_factory
        self.retry = RetryHandler(retry_config or RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0
        ))
        self._connection = None
    
    async def connect(self):
        """Connect with retry"""
        self._connection = await self.retry.execute(self.connection_factory)
        return self._connection
    
    async def execute(self, query: str, *args, **kwargs):
        """Execute with retry on connection errors"""
        try:
            return await self._connection.execute(query, *args, **kwargs)
        except Exception as e:
            # Check if connection error
            error_str = str(e).lower()
            if any(kw in error_str for kw in ['connection', 'closed', 'broken']):
                # Reconnect and retry
                await self.connect()
                return await self._connection.execute(query, *args, **kwargs)
            raise


class LLMFallbackHandler:
    """
    Handle LLM failures with fallback to cached responses.
    """
    
    def __init__(self, cache_client):
        self.cache = cache_client
        self.fallback_responses: Dict[str, Any] = {}
    
    def register_fallback(self, key: str, response: Any):
        """Register a fallback response"""
        self.fallback_responses[key] = response
    
    async def execute_with_fallback(
        self,
        llm_func: Callable,
        cache_key: Optional[str] = None,
        fallback_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute LLM call with fallback on failure.
        """
        # Try cache first
        if cache_key:
            cached = await self.cache.get(cache_key)
            if cached:
                return {
                    "success": True,
                    "data": cached,
                    "source": "cache"
                }
        
        # Try LLM call
        try:
            result = await llm_func(*args, **kwargs)
            
            # Cache successful result
            if cache_key:
                await self.cache.set(cache_key, result, ttl=3600)
            
            return {
                "success": True,
                "data": result,
                "source": "llm"
            }
            
        except Exception as e:
            # Try fallback
            if fallback_key and fallback_key in self.fallback_responses:
                return {
                    "success": True,
                    "data": self.fallback_responses[fallback_key],
                    "source": "fallback",
                    "warning": f"LLM failed, using fallback: {str(e)}"
                }
            
            # Try cached stale result
            if cache_key:
                cached = await self.cache.get(f"{cache_key}:stale")
                if cached:
                    return {
                        "success": True,
                        "data": cached,
                        "source": "stale_cache",
                        "warning": f"LLM failed, using stale cache: {str(e)}"
                    }
            
            # All fallbacks exhausted
            return {
                "success": False,
                "error": ErrorClassifier.classify(e).to_dict()
            }


class PartialResultHandler:
    """
    Handle partial results from failed operations.
    """
    
    def __init__(self):
        self.partial_results: List[Any] = []
        self.errors: List[AppError] = []
    
    def add_partial(self, result: Any):
        """Add a partial result"""
        self.partial_results.append(result)
    
    def add_error(self, error: AppError):
        """Add an error"""
        self.errors.append(error)
    
    def get_result(self) -> Dict[str, Any]:
        """Get combined result with errors"""
        return {
            "success": len(self.errors) == 0,
            "partial": len(self.errors) > 0 and len(self.partial_results) > 0,
            "data": self.partial_results,
            "errors": [e.to_dict() for e in self.errors],
            "total_parts": len(self.partial_results) + len(self.errors),
            "successful_parts": len(self.partial_results)
        }


def create_error_response(
    exception: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """Create standardized error response"""
    app_error = ErrorClassifier.classify(exception)
    response = app_error.to_dict()
    
    if include_traceback:
        import traceback
        response["traceback"] = traceback.format_exc()
    
    return response
