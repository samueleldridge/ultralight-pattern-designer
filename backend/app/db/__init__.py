"""Database module initialization."""

from app.db.connection import (
    ConnectionPoolManager,
    ConnectionPoolConfig,
    RetryConfig,
    DatabaseManager,
    with_retry,
    get_db_session,
    get_analytics_session,
    execute_analytics_query,
)

from app.db.indexes import (
    get_index_definitions,
    get_index_recommendations,
    get_maintenance_sql,
)

from app.db.validation import (
    DataValidator,
    AuditLogger,
    AuditAction,
    AuditRecord,
    ValidationContext,
    setup_audit_listeners,
)

__all__ = [
    # Connection management
    "ConnectionPoolManager",
    "ConnectionPoolConfig",
    "RetryConfig",
    "DatabaseManager",
    "with_retry",
    "get_db_session",
    "get_analytics_session",
    "execute_analytics_query",
    
    # Indexes
    "get_index_definitions",
    "get_index_recommendations",
    "get_maintenance_sql",
    
    # Validation and audit
    "DataValidator",
    "AuditLogger",
    "AuditAction",
    "AuditRecord",
    "ValidationContext",
    "setup_audit_listeners",
]
