"""
Enhanced database executor with edge case handling.
Includes timeouts, row limits, retry logic, and comprehensive security.
"""

import asyncio
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.cache import get_enhanced_cache, cached_query
from app.config import get_settings
from app.middleware import (
    enforce_query_limits,
    add_query_limits,
    DEFAULT_LIMITS,
    QueryLimits
)
from app.security import (
    validate_sql_security,
    SQLInjectionDetector,
    QuerySanitizer,
    get_audit_logger,
)
from app.monitoring import (
    get_monitor,
    RetryConfig,
    RetryHandler,
    track_query,
)
from app.database.connector import DatabaseConfig, DatabaseConnector
from app.database.dialect import SQLValidator, SQLDialect


class EnhancedQueryExecutor:
    """
    Enhanced query executor with comprehensive edge case handling.
    Features:
    - Query timeouts
    - Row limits
    - Security validation
    - Caching
    - Retry logic
    - Audit logging
    - Performance monitoring
    """
    
    def __init__(self):
        self.cache = get_enhanced_cache()
        self.audit = get_audit_logger()
        self.monitor = get_monitor()
        self.retry_handler = RetryHandler(RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0
        ))
        self.active_queries: Dict[str, Any] = {}
    
    async def execute(
        self,
        query: str,
        config: DatabaseConfig,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_cache: bool = True,
        timeout_seconds: int = 30,
        limits: Optional[QueryLimits] = None,
        enforce_limits: bool = True
    ) -> Dict[str, Any]:
        """
        Execute query with full edge case handling.
        """
        connection_id = f"{config.host}:{config.database}"
        limits = limits or DEFAULT_LIMITS
        
        # Generate query hash for tracking
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        
        # Start monitoring
        metric_id = self.monitor.start_query(
            query_hash, query, user_id, tenant_id, connection_id
        )
        
        try:
            # 1. Validate SQL security
            security_result = validate_sql_security(query)
            if not security_result.passed:
                await self.audit.log_security_violation(
                    "sql_injection_attempt",
                    {"query_hash": query_hash, "issues": security_result.issues},
                    user_id=user_id,
                    tenant_id=tenant_id
                )
                
                return {
                    "success": False,
                    "error": "Security violation",
                    "details": security_result.issues
                }
            
            # Use sanitized query
            query = security_result.sanitized_query or query
            
            # 2. Check cache
            if use_cache:
                cached = await self.cache.get_query_result(
                    query, connection_id, user_id=user_id
                )
                if cached:
                    self.monitor.end_query(metric_id, cache_hit=True)
                    return {
                        "success": True,
                        "data": cached["result"],
                        "from_cache": True,
                        "row_count": cached["result"].get("row_count", 0)
                    }
            
            # 3. Enforce query limits
            if enforce_limits:
                limit_check = enforce_query_limits(query, limits)
                
                # Add row limit to query
                query = add_query_limits(query, limits)
            
            # 4. Validate dialect
            validator = SQLValidator(SQLDialect(config.db_type))
            validation = validator.validate(query)
            
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "Validation failed",
                    "details": validation["errors"]
                }
            
            # 5. Execute with timeout
            connector = DatabaseConnector(config)
            
            try:
                rows = await asyncio.wait_for(
                    connector.execute(query),
                    timeout=timeout_seconds
                )
                
                # Enforce row limit post-execution
                if len(rows) > limits.max_rows_returned:
                    rows = rows[:limits.max_rows_returned]
                
                result = {
                    "rows": rows,
                    "row_count": len(rows),
                    "columns": list(rows[0].keys()) if rows else []
                }
                
                # 6. Cache result
                if use_cache:
                    await self.cache.set_query_result(
                        query, connection_id, result, user_id=user_id
                    )
                
                # 7. Log to audit
                await self.audit.log_query(
                    sql=query,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    row_count=len(rows),
                    success=True
                )
                
                # 8. End monitoring
                self.monitor.end_query(metric_id, row_count=len(rows))
                
                return {
                    "success": True,
                    "data": result,
                    "from_cache": False,
                    "warnings": validation.get("warnings", [])
                }
                
            except asyncio.TimeoutError:
                self.monitor.end_query(
                    metric_id,
                    error=f"Query timed out after {timeout_seconds} seconds"
                )
                
                return {
                    "success": False,
                    "error": f"Query timed out after {timeout_seconds} seconds",
                    "suggestion": "Try adding LIMIT or more specific filters",
                    "code": "QUERY_TIMEOUT"
                }
                
            except Exception as e:
                self.monitor.end_query(metric_id, error=str(e))
                raise
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            # Log error
            await self.audit.log_query(
                sql=query,
                user_id=user_id,
                tenant_id=tenant_id,
                connection_id=connection_id,
                success=False,
                error=str(e)
            )
            
            from app.monitoring import create_error_response
            return create_error_response(e)
    
    async def execute_with_retry(
        self,
        query: str,
        config: DatabaseConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute with automatic retry on transient failures"""
        async def _execute():
            return await self.execute(query, config, **kwargs)
        
        try:
            return await self.retry_handler.execute(_execute)
        except Exception as e:
            from app.monitoring import create_error_response
            return create_error_response(e)
    
    async def explain_query(
        self,
        query: str,
        config: DatabaseConfig
    ) -> Dict[str, Any]:
        """Get query execution plan"""
        connector = DatabaseConnector(config)
        
        try:
            await connector.connect()
            
            if config.db_type == 'postgresql':
                explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE false) {query}"
            elif config.db_type == 'mysql':
                explain_query = f"EXPLAIN FORMAT=JSON {query}"
            else:
                return {
                    "success": False,
                    "error": "EXPLAIN not supported for this database type"
                }
            
            result = await connector.execute(explain_query)
            
            return {
                "success": True,
                "plan": result[0] if result else None,
                "dialect": config.db_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await connector.disconnect()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        return {
            "monitor": self.monitor.get_stats(),
            "active_queries": len(self.active_queries)
        }


# Global executor instance
_executor_instance: Optional[EnhancedQueryExecutor] = None


def get_executor() -> EnhancedQueryExecutor:
    """Get global executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = EnhancedQueryExecutor()
    return _executor_instance


# Backward compatibility with existing code
class QueryCache:
    """Legacy QueryCache - delegates to enhanced cache"""
    
    def __init__(self):
        self._cache = get_enhanced_cache()
    
    async def get(self, query: str, connection_id: str):
        return await self._cache.get_query_result(query, connection_id)
    
    async def set(self, query: str, connection_id: str, result: Dict, **kwargs):
        await self._cache.set_query_result(query, connection_id, result)


class QueryExecutor:
    """Legacy QueryExecutor - delegates to enhanced executor"""
    
    def __init__(self):
        self._executor = get_executor()
        self.cache = QueryCache()
    
    async def execute(
        self,
        query: str,
        config: DatabaseConfig,
        use_cache: bool = True,
        timeout_seconds: int = 30
    ):
        return await self._executor.execute(
            query, config,
            use_cache=use_cache,
            timeout_seconds=timeout_seconds
        )
    
    async def explain_query(self, query: str, config: DatabaseConfig):
        return await self._executor.explain_query(query, config)
