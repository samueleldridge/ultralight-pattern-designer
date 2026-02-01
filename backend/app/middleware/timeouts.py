"""
Query timeout and limits middleware.
Enforces execution time limits, row limits, and complexity limits.
"""

import asyncio
import re
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


@dataclass
class QueryLimits:
    """Configuration for query limits"""
    max_execution_time_seconds: int = 30
    max_rows_returned: int = 10000
    max_joins: int = 5
    max_subqueries: int = 3
    max_query_length: int = 10000
    allow_cartesian_product: bool = False
    require_where_clause: bool = False  # For large tables


class QueryLimitExceeded(HTTPException):
    """Raised when query exceeds limits"""
    def __init__(self, detail: str, limit_type: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Query limit exceeded",
                "type": limit_type,
                "message": detail
            }
        )


class QueryComplexityAnalyzer:
    """Analyze SQL query complexity"""
    
    def __init__(self, sql: str):
        self.sql = sql.upper()
    
    def count_joins(self) -> int:
        """Count number of JOIN clauses"""
        join_patterns = [
            r'\bINNER\s+JOIN\b',
            r'\bLEFT\s+JOIN\b',
            r'\bRIGHT\s+JOIN\b',
            r'\bFULL\s+JOIN\b',
            r'\bCROSS\s+JOIN\b',
            r'\bJOIN\b'  # Simple JOIN
        ]
        count = 0
        for pattern in join_patterns:
            matches = re.findall(pattern, self.sql)
            count += len(matches)
        return count
    
    def count_subqueries(self) -> int:
        """Count number of subqueries"""
        # Count nested SELECT statements
        return len(re.findall(r'\(\s*SELECT\s+', self.sql, re.IGNORECASE))
    
    def has_cartesian_product(self) -> bool:
        """Check for potential cartesian products"""
        # Multiple tables in FROM without JOIN
        from_match = re.search(r'FROM\s+([^)]+?)(?:WHERE|GROUP|ORDER|LIMIT|$)', self.sql, re.IGNORECASE)
        if from_match:
            from_clause = from_match.group(1)
            # Count tables (comma-separated)
            tables = [t.strip() for t in from_clause.split(',') if t.strip()]
            if len(tables) > 1:
                # Check if there are proper JOINs for all tables
                for i in range(1, len(tables)):
                    # If there's a comma-separated table without a JOIN, it's a cartesian product
                    if i < len(tables) and not re.search(rf'JOIN\s+{re.escape(tables[i])}', self.sql, re.IGNORECASE):
                        return True
        return False
    
    def has_where_clause(self) -> bool:
        """Check if query has WHERE clause"""
        return bool(re.search(r'\bWHERE\b', self.sql, re.IGNORECASE))
    
    def is_complex_query(self) -> Dict[str, Any]:
        """Return complexity analysis"""
        return {
            "joins": self.count_joins(),
            "subqueries": self.count_subqueries(),
            "has_cartesian_product": self.has_cartesian_product(),
            "has_where_clause": self.has_where_clause(),
            "length": len(self.sql)
        }


class QueryTimeoutManager:
    """Manage query execution with timeouts"""
    
    def __init__(self, default_timeout_seconds: int = 30):
        self.default_timeout = default_timeout_seconds
    
    async def execute_with_timeout(
        self,
        coro: Callable,
        timeout_seconds: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute coroutine with timeout"""
        timeout = timeout_seconds or self.default_timeout
        
        try:
            return await asyncio.wait_for(
                coro(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise QueryLimitExceeded(
                f"Query execution exceeded {timeout} seconds timeout",
                "timeout"
            )


class QueryLimitsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce query limits on API endpoints.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        limits: Optional[QueryLimits] = None,
        check_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.limits = limits or QueryLimits()
        self.check_paths = check_paths or ["/api/query"]
    
    async def dispatch(self, request: Request, call_next):
        # Only check specific paths
        if not any(request.url.path.startswith(path) for path in self.check_paths):
            return await call_next(request)
        
        # Check query size for POST requests
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                size = int(content_length)
                if size > self.limits.max_query_length * 2:  # Allow some overhead
                    raise QueryLimitExceeded(
                        f"Request body too large. Max query length: {self.limits.max_query_length}",
                        "size_limit"
                    )
        
        response = await call_next(request)
        
        # Add query limits headers
        response.headers["X-Query-Max-Rows"] = str(self.limits.max_rows_returned)
        response.headers["X-Query-Max-Time"] = str(self.limits.max_execution_time_seconds)
        
        return response


def enforce_query_limits(
    sql: str,
    limits: Optional[QueryLimits] = None,
    table_row_counts: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Enforce query limits on SQL.
    Returns analysis or raises QueryLimitExceeded.
    """
    limits = limits or QueryLimits()
    analyzer = QueryComplexityAnalyzer(sql)
    analysis = analyzer.is_complex_query()
    
    # Check query length
    if analysis["length"] > limits.max_query_length:
        raise QueryLimitExceeded(
            f"Query too long ({analysis['length']} chars). Max: {limits.max_query_length}",
            "length"
        )
    
    # Check JOIN limit
    if analysis["joins"] > limits.max_joins:
        raise QueryLimitExceeded(
            f"Too many JOINs ({analysis['joins']}). Max: {limits.max_joins}",
            "join_limit"
        )
    
    # Check subquery limit
    if analysis["subqueries"] > limits.max_subqueries:
        raise QueryLimitExceeded(
            f"Too many subqueries ({analysis['subqueries']}). Max: {limits.max_subqueries}",
            "subquery_limit"
        )
    
    # Check cartesian product
    if not limits.allow_cartesian_product and analysis["has_cartesian_product"]:
        raise QueryLimitExceeded(
            "Query contains cartesian product (multiple tables without proper JOINs). "
            "This can cause extremely slow queries.",
            "cartesian_product"
        )
    
    # Check for WHERE clause on large tables
    if limits.require_where_clause:
        # Check if any large table lacks a WHERE clause
        if table_row_counts:
            large_tables = {t: c for t, c in table_row_counts.items() if c > 100000}
            if large_tables and not analysis["has_where_clause"]:
                raise QueryLimitExceeded(
                    "Query on large table requires WHERE clause",
                    "missing_where"
                )
    
    return {
        "valid": True,
        "complexity": analysis,
        "limits": {
            "max_rows": limits.max_rows_returned,
            "max_time_seconds": limits.max_execution_time_seconds
        }
    }


def add_query_limits(
    sql: str,
    limits: Optional[QueryLimits] = None
) -> str:
    """
    Add limit clauses to SQL if not present.
    Ensures row limits are enforced at the database level.
    """
    limits = limits or QueryLimits()
    
    sql_upper = sql.upper()
    
    # Check if already has LIMIT
    if "LIMIT" in sql_upper:
        # Extract current limit and ensure it's not over max
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit > limits.max_rows_returned:
                # Replace with lower limit
                sql = re.sub(
                    r'LIMIT\s+\d+',
                    f'LIMIT {limits.max_rows_returned}',
                    sql,
                    flags=re.IGNORECASE
                )
        return sql
    
    # Add LIMIT clause
    # Need to insert before ORDER BY if present, otherwise at end
    if "ORDER BY" in sql_upper:
        sql = re.sub(
            r'(ORDER\s+BY\s+.+?)(?:\s*$|(?:\s+LIMIT\s+))',
            rf'\1 LIMIT {limits.max_rows_returned}',
            sql,
            flags=re.IGNORECASE
        )
    else:
        sql = f"{sql.rstrip('; ')} LIMIT {limits.max_rows_returned}"
    
    return sql


# Pre-configured limit sets
STRICT_LIMITS = QueryLimits(
    max_execution_time_seconds=10,
    max_rows_returned=1000,
    max_joins=2,
    max_subqueries=1,
    allow_cartesian_product=False,
    require_where_clause=True
)

DEFAULT_LIMITS = QueryLimits(
    max_execution_time_seconds=30,
    max_rows_returned=10000,
    max_joins=5,
    max_subqueries=3,
    allow_cartesian_product=False,
    require_where_clause=False
)

RELAXED_LIMITS = QueryLimits(
    max_execution_time_seconds=60,
    max_rows_returned=50000,
    max_joins=10,
    max_subqueries=5,
    allow_cartesian_product=False,
    require_where_clause=False
)
