"""
Database executor module - backwards compatibility.
New code should use executor_v2.EnhancedQueryExecutor
"""

# Re-export from executor_v2 for backwards compatibility
from app.database.executor_v2 import (
    EnhancedQueryExecutor,
    QueryExecutor,
    QueryCache,
    get_executor,
)

__all__ = [
    "EnhancedQueryExecutor",
    "QueryExecutor",
    "QueryCache",
    "get_executor",
]
