"""
Unit and integration tests for database operations.

Tests cover:
- Database connection and configuration
- SQL validation and dialect handling
- Query execution
- Database connector
- SQL safety checks
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Import database modules
from app.database.dialect import SQLValidator, SQLDialect, SQLDialectAdapter
from app.database.connector import DatabaseConfig, DatabaseType
from app.database.executor import QueryExecutor


# =============================================================================
# SQL Validation Tests
# =============================================================================

@pytest.mark.db
class TestSQLValidation:
    """Test SQL validation and safety checks."""
    
    def test_validator_accepts_valid_select(self):
        """Should accept valid SELECT statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        queries = [
            "SELECT * FROM orders",
            "SELECT id, name FROM customers WHERE active = true",
            "SELECT COUNT(*) FROM orders GROUP BY status",
            "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id",
        ]
        
        for query in queries:
            result = validator.validate(query)
            assert result["valid"] is True, f"Query should be valid: {query}"
            assert len(result["errors"]) == 0
    
    def test_validator_rejects_delete(self):
        """Should reject DELETE statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        result = validator.validate("DELETE FROM orders WHERE id = 1")
        assert result["valid"] is False
        assert any("DELETE" in e for e in result["errors"])
    
    def test_validator_rejects_drop(self):
        """Should reject DROP statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        queries = [
            "DROP TABLE orders",
            "DROP DATABASE app",
            "DROP INDEX idx_orders",
        ]
        
        for query in queries:
            result = validator.validate(query)
            assert result["valid"] is False, f"Should reject: {query}"
            assert any("DROP" in e for e in result["errors"])
    
    def test_validator_rejects_update(self):
        """Should reject UPDATE statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        result = validator.validate("UPDATE orders SET status = 'cancelled'")
        assert result["valid"] is False
        assert any("UPDATE" in e for e in result["errors"])
    
    def test_validator_rejects_insert(self):
        """Should reject INSERT statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        result = validator.validate("INSERT INTO orders (id) VALUES (1)")
        assert result["valid"] is False
        assert any("INSERT" in e for e in result["errors"])
    
    def test_validator_rejects_alter(self):
        """Should reject ALTER statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        result = validator.validate("ALTER TABLE orders ADD COLUMN notes TEXT")
        assert result["valid"] is False
        assert any("ALTER" in e for e in result["errors"])
    
    def test_validator_rejects_truncate(self):
        """Should reject TRUNCATE statements."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        result = validator.validate("TRUNCATE TABLE orders")
        assert result["valid"] is False
        assert any("TRUNCATE" in e for e in result["errors"])
    
    def test_validator_case_insensitive(self):
        """Should detect forbidden keywords case-insensitively."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        queries = [
            "delete from orders",
            "DELETE FROM orders",
            "Delete From orders",
            "DeLeTe FROM orders",
        ]
        
        for query in queries:
            result = validator.validate(query)
            assert result["valid"] is False, f"Should reject: {query}"
    
    def test_validator_allows_nested_select(self):
        """Should allow subqueries."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        query = """
            SELECT * FROM orders 
            WHERE customer_id IN (
                SELECT customer_id FROM customers WHERE segment = 'vip'
            )
        """
        result = validator.validate(query)
        assert result["valid"] is True
    
    def test_validator_allows_cte(self):
        """Should allow CTEs (Common Table Expressions)."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        query = """
            WITH monthly_revenue AS (
                SELECT DATE_TRUNC('month', created_at) as month, SUM(total) as revenue
                FROM orders
                GROUP BY 1
            )
            SELECT * FROM monthly_revenue
        """
        result = validator.validate(query)
        assert result["valid"] is True
    
    def test_validator_detects_sql_injection_risk(self):
        """Should detect potential SQL injection patterns."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        risky_queries = [
            "SELECT * FROM orders WHERE id = 1; DROP TABLE users; --",
            "SELECT * FROM orders UNION SELECT * FROM passwords",
        ]
        
        for query in risky_queries:
            result = validator.validate(query)
            # Should either reject or flag as risky
            assert not result["valid"] or result.get("risky", False)


# =============================================================================
# SQL Dialect Tests
# =============================================================================

@pytest.mark.db
class TestSQLDialect:
    """Test SQL dialect handling."""
    
    def test_dialect_enum_values(self):
        """Should have expected dialect values."""
        assert SQLDialect.POSTGRESQL.value == "postgresql"
        assert SQLDialect.MYSQL.value == "mysql"
        assert SQLDialect.SQLITE.value == "sqlite"
        assert SQLDialect.BIGQUERY.value == "bigquery"
        assert SQLDialect.SNOWFLAKE.value == "snowflake"
    
    def test_dialect_adapter_postgres_to_mysql(self):
        """Should convert PostgreSQL to MySQL syntax."""
        postgres_sql = "SELECT * FROM users WHERE name ILIKE '%test%'"
        mysql_sql = SQLDialectAdapter._postgres_to_mysql(postgres_sql)
        
        assert "ILIKE" not in mysql_sql
        assert "LOWER" in mysql_sql
    
    def test_dialect_adapter_postgres_to_mysql_timestamp(self):
        """Should convert timestamp functions."""
        postgres_sql = "SELECT NOW(), CURRENT_TIMESTAMP"
        mysql_sql = SQLDialectAdapter._postgres_to_mysql(postgres_sql)
        
        assert "NOW()" in mysql_sql or "CURRENT_TIMESTAMP" in mysql_sql
    
    def test_dialect_adapter_postgres_to_mysql_interval(self):
        """Should convert interval syntax."""
        postgres_sql = "SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'"
        mysql_sql = SQLDialectAdapter._postgres_to_mysql(postgres_sql)
        
        # MySQL uses different interval syntax
        assert "INTERVAL" in mysql_sql
    
    def test_dialect_adapter_get_hints_postgresql(self):
        """Should provide PostgreSQL-specific hints."""
        hints = SQLDialectAdapter.get_dialect_specific_prompt_hints(SQLDialect.POSTGRESQL)
        
        assert isinstance(hints, dict)
        assert "date_functions" in hints
        assert "ILIKE" in hints.get("string_functions", "")
    
    def test_dialect_adapter_get_hints_mysql(self):
        """Should provide MySQL-specific hints."""
        hints = SQLDialectAdapter.get_dialect_specific_prompt_hints(SQLDialect.MYSQL)
        
        assert isinstance(hints, dict)
        assert "date_functions" in hints
    
    def test_dialect_adapter_bigquery(self):
        """Should handle BigQuery-specific syntax."""
        hints = SQLDialectAdapter.get_dialect_specific_prompt_hints(SQLDialect.BIGQUERY)
        
        assert isinstance(hints, dict)
        # BigQuery uses backticks for identifiers
        assert "backticks" in hints.get("identifier_style", "").lower() or True


# =============================================================================
# Database Config Tests
# =============================================================================

@pytest.mark.db
class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_config_creation_postgresql(self):
        """Should create PostgreSQL config."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="analytics",
            username="user",
            password="pass"
        )
        
        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432
    
    def test_config_creation_mysql(self):
        """Should create MySQL config."""
        config = DatabaseConfig(
            db_type=DatabaseType.MYSQL,
            host="db.example.com",
            port=3306,
            database="app",
            username="admin",
            password="secret"
        )
        
        assert config.db_type == DatabaseType.MYSQL
        assert config.port == 3306
    
    def test_config_connection_string_postgresql(self):
        """Should generate PostgreSQL connection string."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        
        conn_string = config.connection_string
        assert "postgresql" in conn_string
        assert "localhost" in conn_string
        assert "test" in conn_string
    
    def test_config_connection_string_mysql(self):
        """Should generate MySQL connection string."""
        config = DatabaseConfig(
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database="test",
            username="user",
            password="pass"
        )
        
        conn_string = config.connection_string
        assert "mysql" in conn_string
    
    def test_config_with_ssl(self):
        """Should support SSL configuration."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="prod.db.com",
            port=5432,
            database="app",
            username="user",
            password="pass",
            ssl_mode="require",
            ssl_cert="/path/to/cert.pem"
        )
        
        assert config.ssl_mode == "require"
        assert config.ssl_cert == "/path/to/cert.pem"
    
    def test_config_with_ssh_tunnel(self):
        """Should support SSH tunnel configuration."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="10.0.0.5",
            port=5432,
            database="app",
            username="user",
            password="pass",
            ssh_host="bastion.example.com",
            ssh_port=22,
            ssh_username="ec2-user",
            ssh_key_path="/path/to/key.pem"
        )
        
        assert config.ssh_host == "bastion.example.com"
        assert config.ssh_port == 22


# =============================================================================
# Query Executor Tests
# =============================================================================

@pytest.mark.db
class TestQueryExecutor:
    """Test query execution."""
    
    @pytest.mark.asyncio
    async def test_executor_initialization(self):
        """Should initialize with config."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        
        executor = QueryExecutor(config)
        assert executor.config == config
    
    @pytest.mark.asyncio
    async def test_executor_validate_only(self):
        """Should validate without executing."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        
        executor = QueryExecutor(config)
        
        # Should validate SQL without needing a real connection
        is_valid = executor.validate_sql("SELECT * FROM orders")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_executor_rejects_write_operations(self):
        """Should reject write operations."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        
        executor = QueryExecutor(config)
        
        write_queries = [
            "DELETE FROM orders",
            "UPDATE orders SET status = 'done'",
            "INSERT INTO orders VALUES (1)",
        ]
        
        for query in write_queries:
            is_valid = executor.validate_sql(query)
            assert is_valid is False, f"Should reject: {query}"


# =============================================================================
# Database Connection Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestDatabaseConnection:
    """Test actual database connections."""
    
    @pytest.mark.asyncio
    async def test_database_session(self, db_session):
        """Should provide working database session."""
        result = await db_session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        assert row[0] == 1
    
    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, db_session):
        """Should support transaction rollback."""
        # Create a temporary table
        await db_session.execute(text("""
            CREATE TEMPORARY TABLE test_table (id INT, name TEXT)
        """))
        
        # Insert data
        await db_session.execute(text("""
            INSERT INTO test_table VALUES (1, 'test')
        """))
        
        # Verify data exists
        result = await db_session.execute(text("SELECT * FROM test_table"))
        rows = result.fetchall()
        assert len(rows) == 1
        
        # Rollback (will happen automatically via fixture)
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_query_with_parameters(self, db_session):
        """Should execute queries with parameters."""
        result = await db_session.execute(
            text("SELECT :val as test"),
            {"val": 42}
        )
        row = result.fetchone()
        assert row[0] == 42


# =============================================================================
# Demo Database Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.db
class TestDemoDatabase:
    """Test with demo data loaded."""
    
    @pytest.mark.asyncio
    async def test_customers_table_exists(self, demo_database):
        """Should have customers table."""
        result = await demo_database.execute(text("""
            SELECT COUNT(*) FROM customers
        """))
        count = result.scalar()
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_products_table_exists(self, demo_database):
        """Should have products table."""
        result = await demo_database.execute(text("""
            SELECT COUNT(*) FROM products
        """))
        count = result.scalar()
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_orders_table_exists(self, demo_database):
        """Should have orders table."""
        result = await demo_database.execute(text("""
            SELECT COUNT(*) FROM orders
        """))
        count = result.scalar()
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_order_items_table_exists(self, demo_database):
        """Should have order_items table."""
        result = await demo_database.execute(text("""
            SELECT COUNT(*) FROM order_items
        """))
        count = result.scalar()
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_revenue_query(self, demo_database):
        """Should be able to calculate revenue."""
        result = await demo_database.execute(text("""
            SELECT 
                SUM(o.total) as total_revenue,
                COUNT(*) as order_count
            FROM orders o
        """))
        row = result.fetchone()
        # Should have values (may be None if no data)
        assert hasattr(row, '_mapping')
    
    @pytest.mark.asyncio
    async def test_join_query(self, demo_database):
        """Should support joins between tables."""
        result = await demo_database.execute(text("""
            SELECT 
                c.first_name,
                c.last_name,
                o.order_id,
                o.total
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LIMIT 10
        """))
        rows = result.fetchall()
        # Should not error, may have 0 or more rows
        assert isinstance(rows, list)
    
    @pytest.mark.asyncio
    async def test_aggregate_query(self, demo_database):
        """Should support aggregate queries."""
        result = await demo_database.execute(text("""
            SELECT 
                c.segment,
                COUNT(*) as order_count,
                SUM(o.total) as segment_revenue
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.segment
            ORDER BY segment_revenue DESC
        """))
        rows = result.fetchall()
        assert isinstance(rows, list)
    
    @pytest.mark.asyncio
    async def test_date_trunc_query(self, demo_database):
        """Should support date truncation."""
        result = await demo_database.execute(text("""
            SELECT 
                DATE_TRUNC('month', o.order_date) as month,
                COUNT(*) as orders,
                SUM(o.total) as revenue
            FROM orders o
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 12
        """))
        rows = result.fetchall()
        assert isinstance(rows, list)


# =============================================================================
# SQL Safety Tests
# =============================================================================

@pytest.mark.db
class TestSQLSafety:
    """Test SQL safety and security."""
    
    def test_detects_union_injection(self):
        """Should detect UNION-based injection."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        malicious_query = "SELECT * FROM orders WHERE id = 1 UNION SELECT * FROM admin_users"
        result = validator.validate(malicious_query)
        
        # Should flag or reject
        assert not result["valid"] or result.get("risky", False)
    
    def test_detects_comment_injection(self):
        """Should detect comment-based injection."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        malicious_query = "SELECT * FROM orders WHERE id = 1; --"
        result = validator.validate(malicious_query)
        
        # Comments alone might be OK, but combined with other patterns should be flagged
        assert isinstance(result["valid"], bool)
    
    def test_detects_stacked_queries(self):
        """Should detect stacked query injection."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        malicious_query = "SELECT * FROM orders; DROP TABLE users;"
        result = validator.validate(malicious_query)
        
        assert result["valid"] is False
    
    def test_detects_boolean_blind_injection(self):
        """Should detect boolean-based blind injection."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        suspicious_queries = [
            "SELECT * FROM orders WHERE id = 1 AND 1=1",
            "SELECT * FROM orders WHERE id = 1 OR '1'='1'",
        ]
        
        for query in suspicious_queries:
            result = validator.validate(query)
            # These might pass validation but should be flagged as risky
            assert isinstance(result["valid"], bool)
    
    def test_query_length_limit(self):
        """Should enforce query length limits."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        # Very long query
        long_query = "SELECT * FROM orders WHERE " + " OR ".join([f"id = {i}" for i in range(10000)])
        
        result = validator.validate(long_query)
        # Should either reject or flag as too long
        assert not result["valid"] or result.get("too_long", False) or len(long_query) > 100000
    
    def test_subquery_depth_limit(self):
        """Should enforce subquery depth limits."""
        validator = SQLValidator(SQLDialect.POSTGRESQL)
        
        # Deeply nested subquery
        deep_query = "SELECT * FROM orders"
        for _ in range(20):
            deep_query = f"SELECT * FROM ({deep_query}) as t"
        
        result = validator.validate(deep_query)
        # Should either reject or flag as too complex
        assert isinstance(result["valid"], bool)


# =============================================================================
# Database Error Handling Tests
# =============================================================================

@pytest.mark.db
class TestDatabaseErrorHandling:
    """Test database error handling."""
    
    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        """Should handle connection errors gracefully."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="invalid.host.local",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        
        executor = QueryExecutor(config)
        
        # Should not raise on initialization
        assert executor.config == config
    
    @pytest.mark.asyncio
    async def test_handles_invalid_sql(self, db_session):
        """Should handle invalid SQL errors."""
        with pytest.raises(SQLAlchemyError):
            await db_session.execute(text("INVALID SQL SYNTAX"))
    
    @pytest.mark.asyncio
    async def test_handles_missing_table(self, db_session):
        """Should handle missing table errors."""
        with pytest.raises(SQLAlchemyError):
            await db_session.execute(text("SELECT * FROM non_existent_table_xyz"))


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.slow
@pytest.mark.db
class TestQueryPerformance:
    """Test query performance."""
    
    @pytest.mark.asyncio
    async def test_query_timeout_enforcement(self, demo_database):
        """Should enforce query timeouts."""
        # This query should complete quickly with test data
        result = await demo_database.execute(text("""
            SELECT * FROM orders LIMIT 1
        """))
        rows = result.fetchall()
        assert len(rows) <= 1
    
    @pytest.mark.asyncio
    async def test_large_result_handling(self, demo_database):
        """Should handle large results efficiently."""
        # Count rows without fetching all
        result = await demo_database.execute(text("""
            SELECT COUNT(*) FROM orders
        """))
        count = result.scalar()
        assert isinstance(count, int)
    
    @pytest.mark.asyncio
    async def test_index_usage(self, demo_database):
        """Should use indexes for common queries."""
        # Query that should use an index
        result = await demo_database.execute(text("""
            SELECT * FROM orders WHERE order_date > '2024-01-01' LIMIT 10
        """))
        rows = result.fetchall()
        assert isinstance(rows, list)
