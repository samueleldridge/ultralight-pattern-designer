"""
Database module - Maintains backward compatibility while integrating
with the new connection pooling and management system.

For new code, prefer using:
    from app.db.connection import get_db_session, DatabaseManager
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import get_settings

settings = get_settings()

# =============================================================================
# Legacy Engine (for backward compatibility)
# =============================================================================

# Create async engine with connection pooling settings
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


# =============================================================================
# Legacy Functions (backward compatible)
# =============================================================================

async def get_db():
    """Dependency for getting database session (backward compatible)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Create pgvector extension (PostgreSQL only)
        if "sqlite" not in settings.database_url:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create tables
        await conn.run_sync(Base.metadata.create_all)


# =============================================================================
# New Database Management (recommended for new code)
# =============================================================================

async def init_database_manager():
    """Initialize the new DatabaseManager with connection pooling."""
    from app.db.connection import DatabaseManager
    
    manager = await DatabaseManager.get_instance()
    manager.initialize(settings)
    return manager


async def get_optimized_db():
    """
    Get database session using the new optimized connection pool.
    Recommended for new code.
    """
    from app.db.connection import get_db_session
    
    async for session in get_db_session():
        yield session


async def get_analytics_db():
    """
    Get database session optimized for analytical queries.
    Use for long-running aggregations and reports.
    """
    from app.db.connection import get_analytics_session
    
    async for session in get_analytics_session():
        yield session
