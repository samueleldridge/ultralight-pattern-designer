"""
Database module - backwards compatibility and new features.
"""

# Legacy exports (backward compatibility)
from app.database_legacy import (
    engine,
    AsyncSessionLocal,
    Base,
    get_db,
    init_db,
)

# New database features
from app.database.executor import QueryExecutor
from app.database.executor_v2 import EnhancedQueryExecutor, QueryCache, get_executor
from app.database.connector import DatabaseConfig, DatabaseConnector
from app.database.dialect import SQLDialect, SQLValidator

__all__ = [
    # Legacy
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "init_db",
    # New executors
    "QueryExecutor",
    "EnhancedQueryExecutor",
    "QueryCache",
    "get_executor",
    # Connector
    "DatabaseConfig",
    "DatabaseConnector",
    # Dialect
    "SQLDialect",
    "SQLValidator",
]
