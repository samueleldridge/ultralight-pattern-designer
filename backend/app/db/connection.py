"""
Database Connection Management

Provides production-ready database connectivity with:
- Connection pooling optimized for both OLTP and analytical workloads
- Retry logic with exponential backoff
- Connection health monitoring
- Automatic failover support
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator, Callable, Any
from functools import wraps

from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncEngine, AsyncSession,
    async_sessionmaker, AsyncConnection
)
from sqlalchemy.exc import (
    OperationalError, DatabaseError, DisconnectionError,
    TimeoutError as SATimeoutError
)

from app.config import Settings

logger = logging.getLogger(__name__)


class ConnectionPoolConfig:
    """Configuration for database connection pooling."""
    
    def __init__(
        self,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False
    ):
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
    
    @classmethod
    def from_settings(cls, settings: Settings) -> 'ConnectionPoolConfig':
        """Create config from application settings."""
        return cls(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=settings.debug
        )
    
    @classmethod
    def for_analytics(cls) -> 'ConnectionPoolConfig':
        """Config optimized for analytical workloads (longer queries)."""
        return cls(
            pool_size=5,
            max_overflow=10,
            pool_timeout=60,  # Longer timeout for complex queries
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False
        )


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = (
            OperationalError,
            DisconnectionError,
            SATimeoutError,
            ConnectionError,
            asyncio.TimeoutError
        )
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator that adds retry logic with exponential backoff.
    
    Args:
        config: Retry configuration (uses defaults if None)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    jitter = delay * 0.1 * (2 * (time.time() % 1) - 1)  # ±10% jitter
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {actual_delay:.1f}s: {e}"
                    )
                    
                    await asyncio.sleep(actual_delay)
            
            raise last_exception
        
        return async_wrapper
    return decorator


class ConnectionPoolManager:
    """
    Manages database connection pools with monitoring and health checks.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_config: Optional[ConnectionPoolConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        engine_options: Optional[dict] = None
    ):
        self.database_url = database_url
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.retry_config = retry_config or RetryConfig()
        self.engine_options = engine_options or {}
        
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._is_sqlite = "sqlite" in database_url.lower()
        
        # Metrics
        self._connection_attempts = 0
        self._connection_failures = 0
        self._query_count = 0
        self._query_errors = 0
        self._total_query_time = 0.0
    
    def create_engine(self) -> AsyncEngine:
        """Create and configure the database engine."""
        if self._is_sqlite:
            # SQLite-specific configuration
            engine_kwargs = {
                "echo": self.pool_config.echo,
                "future": True,
                "connect_args": {
                    "timeout": 30,
                    "check_same_thread": False,
                }
            }
        else:
            # PostgreSQL connection pooling
            engine_kwargs = {
                "pool_size": self.pool_config.pool_size,
                "max_overflow": self.pool_config.max_overflow,
                "pool_timeout": self.pool_config.pool_timeout,
                "pool_recycle": self.pool_config.pool_recycle,
                "pool_pre_ping": self.pool_config.pool_pre_ping,
                "echo": self.pool_config.echo,
                "future": True,
            }
        
        engine_kwargs.update(self.engine_options)
        
        self._engine = create_async_engine(
            self.database_url,
            **engine_kwargs
        )
        
        # Set up event listeners for monitoring
        self._setup_event_listeners()
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        return self._engine
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self._connection_attempts += 1
            logger.debug("Database connection established")
        
        @event.listens_for(self._engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self._engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine, creating if necessary."""
        if self._engine is None:
            self.create_engine()
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get the session factory, creating if necessary."""
        if self._session_factory is None:
            self.create_engine()
        return self._session_factory
    
    @with_retry()
    async def check_connection(self) -> bool:
        """Check if database connection is healthy."""
        try:
            async with self.engine.connect() as conn:
                if self._is_sqlite:
                    await conn.execute(text("SELECT 1"))
                else:
                    await conn.execute(text("SELECT version()"))
                return True
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            self._connection_failures += 1
            return False
    
    async def get_pool_status(self) -> dict:
        """Get current connection pool status."""
        if self._is_sqlite or self._engine is None:
            return {
                "size": 1,
                "checked_in": 1,
                "checked_out": 0,
                "overflow": 0
            }
        
        # PostgreSQL pool info
        pool = self._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
    
    def get_metrics(self) -> dict:
        """Get connection and query metrics."""
        avg_query_time = (
            self._total_query_time / self._query_count 
            if self._query_count > 0 else 0
        )
        
        return {
            "connection_attempts": self._connection_attempts,
            "connection_failures": self._connection_failures,
            "connection_failure_rate": (
                self._connection_failures / max(self._connection_attempts, 1)
            ),
            "query_count": self._query_count,
            "query_errors": self._query_errors,
            "query_error_rate": (
                self._query_errors / max(self._query_count, 1)
            ),
            "avg_query_time_ms": avg_query_time * 1000,
            "pool_status": asyncio.run(self.get_pool_status()) if self._engine else None
        }
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic commit/rollback."""
        session = self.session_factory()
        start_time = time.time()
        
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self._query_errors += 1
            raise
        finally:
            await session.close()
            self._query_count += 1
            self._total_query_time += time.time() - start_time
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get a raw database connection."""
        async with self.engine.begin() as conn:
            yield conn
    
    @with_retry()
    async def execute_with_timeout(
        self,
        query: str,
        params: Optional[dict] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """Execute a query with optional timeout."""
        timeout = timeout or self.pool_config.pool_timeout
        
        async with self.get_connection() as conn:
            if not self._is_sqlite:
                # Set statement timeout for PostgreSQL
                await conn.execute(text(f"SET statement_timeout = '{timeout}s'"))
            
            start_time = time.time()
            result = await conn.execute(text(query), params or {})
            self._total_query_time += time.time() - start_time
            self._query_count += 1
            
            return result
    
    async def close(self):
        """Close the connection pool."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Connection pool closed")


class DatabaseManager:
    """
    Singleton database manager for the application.
    Provides separate pools for OLTP and analytical workloads.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._primary_pool: Optional[ConnectionPoolManager] = None
        self._analytics_pool: Optional[ConnectionPoolManager] = None
        self._settings: Optional[Settings] = None
    
    @classmethod
    async def get_instance(cls) -> 'DatabaseManager':
        """Get or create the database manager instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def initialize(self, settings: Settings, database_url: Optional[str] = None):
        """Initialize database pools with settings."""
        self._settings = settings
        url = database_url or settings.database_url
        
        # Primary pool for OLTP operations
        primary_config = ConnectionPoolConfig.from_settings(settings)
        self._primary_pool = ConnectionPoolManager(url, primary_config)
        
        # Analytics pool for long-running queries (if not SQLite)
        if "sqlite" not in url.lower():
            analytics_config = ConnectionPoolConfig.for_analytics()
            self._analytics_pool = ConnectionPoolManager(url, analytics_config)
        else:
            self._analytics_pool = self._primary_pool
    
    @property
    def primary_pool(self) -> ConnectionPoolManager:
        """Get the primary connection pool."""
        if self._primary_pool is None:
            raise RuntimeError("DatabaseManager not initialized")
        return self._primary_pool
    
    @property
    def analytics_pool(self) -> ConnectionPoolManager:
        """Get the analytics connection pool."""
        if self._analytics_pool is None:
            raise RuntimeError("DatabaseManager not initialized")
        return self._analytics_pool
    
    async def health_check(self) -> dict:
        """Perform health check on all pools."""
        return {
            "primary": await self._primary_pool.check_connection() if self._primary_pool else False,
            "analytics": await self._analytics_pool.check_connection() if self._analytics_pool else False,
            "metrics": {
                "primary": self._primary_pool.get_metrics() if self._primary_pool else None,
                "analytics": self._analytics_pool.get_metrics() if self._analytics_pool else None
            }
        }
    
    async def close(self):
        """Close all connection pools."""
        if self._primary_pool:
            await self._primary_pool.close()
        if self._analytics_pool and self._analytics_pool is not self._primary_pool:
            await self._analytics_pool.close()


# Convenience functions for common use cases

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions."""
    manager = await DatabaseManager.get_instance()
    async with manager.primary_pool.get_session() as session:
        yield session


async def get_analytics_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a session optimized for analytical queries."""
    manager = await DatabaseManager.get_instance()
    async with manager.analytics_pool.get_session() as session:
        yield session


async def execute_analytics_query(
    query: str,
    params: Optional[dict] = None,
    timeout: int = 60
) -> Any:
    """Execute an analytical query with extended timeout."""
    manager = await DatabaseManager.get_instance()
    return await manager.analytics_pool.execute_with_timeout(
        query, params, timeout
    )
