"""
Pytest configuration and fixtures for AI Analytics Platform tests.

This module provides:
- Test database setup and teardown
- Mock fixtures for external services (LLM, Redis)
- Sample data fixtures
- Client fixtures for API testing
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Ensure the app module is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, event

from app.main import app
from app.config import Settings, get_settings
from app.database import Base, get_db
from app.agent.state import AgentState
from app.llm_provider import LLMProvider, get_llm_provider


# =============================================================================
# Test Database Configuration
# =============================================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics_test"
)

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_test_database():
    """
    Setup test database once per session.
    Creates tables and loads demo data.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Create pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass  # Extension may already exist or not available
    
    yield
    
    # Cleanup after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for each test.
    Rolls back transactions after each test for isolation.
    """
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency for testing."""
    async def _get_db():
        try:
            yield db_session
        finally:
            pass
    return _get_db


@pytest.fixture
def test_app(override_get_db) -> FastAPI:
    """Create a test FastAPI app with overridden dependencies."""
    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app) -> TestClient:
    """Provide a synchronous test client."""
    with TestClient(test_app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as ac:
        yield ac


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_provider():
    """Provide a mocked LLM provider."""
    mock = MagicMock(spec=LLMProvider)
    
    # Mock generate method
    mock.generate = AsyncMock(return_value='{"sql": "SELECT * FROM orders", "explanation": "Test", "chart_type": "table", "confidence": 0.9}')
    
    # Mock generate_json method
    mock.generate_json = AsyncMock(return_value={
        "sql": "SELECT * FROM orders",
        "explanation": "Test query",
        "chart_type": "table",
        "confidence": 0.9
    })
    
    # Mock stream method
    async def mock_stream(*args, **kwargs):
        yield "Test"
        yield " response"
    
    mock.stream = mock_stream
    
    return mock


@pytest.fixture
def mock_redis():
    """Provide a mocked Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    return mock


@pytest.fixture(autouse=True)
def mock_external_services(mock_llm_provider, mock_redis):
    """Automatically mock external services for all tests."""
    with patch("app.llm_provider.get_llm_provider", return_value=mock_llm_provider):
        with patch("app.cache.get_redis", return_value=mock_redis):
            with patch("app.cache.redis_client", mock_redis):
                yield


@pytest.fixture
def mock_settings():
    """Provide test settings."""
    return Settings(
        app_name="AI Analytics Platform Test",
        environment="test",
        debug=True,
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6379/1",  # Use DB 1 for tests
        moonshot_api_key="test-moonshot-key",
        openai_api_key="test-openai-key",
        secret_key="test-secret-key-32-chars-long!!",
        jwt_secret_key="test-jwt-secret-key-32-chars!!",
    )


@pytest.fixture(autouse=True)
def override_settings(mock_settings):
    """Override settings for all tests."""
    def _get_settings():
        return mock_settings
    
    with patch("app.config.get_settings", _get_settings):
        with patch("app.agent.nodes.classify.get_settings", _get_settings):
            with patch("app.agent.nodes.generate.get_settings", _get_settings):
                with patch("app.agent.nodes.analyze.get_settings", _get_settings):
                    with patch("app.agent.nodes.error.get_settings", _get_settings):
                        yield


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_state():
    """Provide a sample agent state."""
    return AgentState(
        query="What was revenue last month?",
        tenant_id="tenant-123",
        user_id="user-456",
        workflow_id=f"wf-{uuid.uuid4()}",
        connection_id="conn-789",
        started_at=datetime.utcnow().isoformat(),
        investigation_history=[],
        retry_count=0,
        sql_valid=True,
        needs_clarification=False,
        investigation_complete=False,
        user_context={
            "top_topics": ["revenue", "sales"],
            "preferred_metrics": ["total_revenue", "active_users"],
            "preferred_chart_types": ["line", "bar"]
        },
        schema_context={
            "tables": [
                {
                    "name": "orders",
                    "columns": ["id", "total", "created_at", "user_id"],
                    "description": "Customer orders"
                },
                {
                    "name": "users",
                    "columns": ["id", "email", "created_at"],
                    "description": "User accounts"
                }
            ]
        }
    )


@pytest.fixture
def sample_agent_state_complex():
    """Provide a complex agent state for investigation scenarios."""
    return AgentState(
        query="Why did revenue drop in Q3?",
        tenant_id="tenant-123",
        user_id="user-456",
        workflow_id=f"wf-{uuid.uuid4()}",
        connection_id="conn-789",
        started_at=datetime.utcnow().isoformat(),
        investigation_history=[],
        retry_count=0,
        sql_valid=True,
        needs_clarification=False,
        investigation_complete=False,
        intent="investigate",
        user_context={},
        schema_context={
            "tables": [
                {"name": "orders", "columns": ["id", "total", "created_at"], "description": "Orders"},
                {"name": "order_items", "columns": ["id", "order_id", "product_id", "quantity"], "description": "Order items"},
                {"name": "products", "columns": ["id", "name", "category", "price"], "description": "Products"}
            ]
        }
    )


@pytest.fixture
def sample_sql_queries():
    """Provide sample SQL queries for testing."""
    return {
        "simple_select": "SELECT * FROM orders",
        "with_where": "SELECT * FROM orders WHERE status = 'completed'",
        "with_join": """
            SELECT o.id, o.total, c.email 
            FROM orders o 
            JOIN customers c ON o.customer_id = c.customer_id 
            WHERE o.created_at > '2024-01-01'
        """,
        "with_aggregate": """
            SELECT 
                DATE_TRUNC('month', created_at) as month,
                SUM(total) as revenue,
                COUNT(*) as order_count
            FROM orders
            GROUP BY 1
            ORDER BY 1
        """,
        "with_subquery": """
            SELECT * FROM orders 
            WHERE customer_id IN (
                SELECT customer_id FROM customers 
                WHERE segment = 'vip'
            )
        """,
        "invalid_syntax": "SELEC * FRM orders",
        "forbidden_delete": "DELETE FROM orders WHERE id = 1",
        "forbidden_update": "UPDATE orders SET status = 'cancelled'",
        "forbidden_drop": "DROP TABLE orders",
    }


@pytest.fixture
def sample_execution_result():
    """Provide a sample query execution result."""
    return {
        "rows": [
            {"month": "2024-01-01", "revenue": 150000.00, "order_count": 450},
            {"month": "2024-02-01", "revenue": 165000.00, "order_count": 520},
            {"month": "2024-03-01", "revenue": 142000.00, "order_count": 410},
        ],
        "row_count": 3,
        "columns": ["month", "revenue", "order_count"]
    }


@pytest.fixture
def sample_query_request():
    """Provide a sample query request."""
    return {
        "query": "What was revenue last month?",
        "tenant_id": "tenant-123",
        "user_id": "user-456",
        "connection_id": "conn-789"
    }


@pytest.fixture
def sample_dashboard_create():
    """Provide a sample dashboard creation request."""
    return {
        "name": "Sales Dashboard",
        "description": "Overview of sales metrics",
        "is_default": False
    }


@pytest.fixture
def sample_connection_config():
    """Provide a sample database connection config."""
    return {
        "name": "Production DB",
        "db_type": "postgresql",
        "host": "db.example.com",
        "port": 5432,
        "database": "analytics",
        "username": "analytics_user",
        "password": "secret_password"
    }


# =============================================================================
# Helper Functions
# =============================================================================

@pytest.fixture
def assert_state_transition():
    """Helper to assert agent state transitions."""
    def _assert(prev_state: AgentState, next_state: AgentState, 
                expected_step: str = None, expected_status: str = None):
        assert next_state["workflow_id"] == prev_state["workflow_id"]
        if expected_step:
            assert next_state["current_step"] == expected_step
        if expected_status:
            assert next_state["step_status"] == expected_status
    return _assert


@pytest.fixture
def create_mock_llm_response():
    """Helper to create mock LLM responses."""
    def _create(**kwargs):
        defaults = {
            "sql": "SELECT * FROM orders",
            "explanation": "Mock explanation",
            "chart_type": "table",
            "confidence": 0.9
        }
        defaults.update(kwargs)
        return defaults
    return _create


# =============================================================================
# Database Setup Helpers
# =============================================================================

async def setup_demo_tables(session: AsyncSession):
    """Create demo tables for testing."""
    # Create tables manually for tests
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id VARCHAR(20) PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20),
            region VARCHAR(10) NOT NULL,
            country VARCHAR(5) NOT NULL,
            state VARCHAR(50),
            city VARCHAR(50),
            postal_code VARCHAR(20),
            segment VARCHAR(20) NOT NULL,
            ltv_factor DECIMAL(3,2),
            churn_risk DECIMAL(3,2),
            created_at TIMESTAMP,
            last_login TIMESTAMP
        )
    """))
    
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(20) PRIMARY KEY,
            sku VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50) NOT NULL,
            description TEXT,
            base_price DECIMAL(10,2) NOT NULL,
            cost DECIMAL(10,2),
            margin DECIMAL(4,2),
            stock_quantity INTEGER,
            is_active BOOLEAN,
            created_at DATE
        )
    """))
    
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(20) PRIMARY KEY,
            customer_id VARCHAR(20) REFERENCES customers(customer_id),
            order_date TIMESTAMP NOT NULL,
            status VARCHAR(20) NOT NULL,
            payment_method VARCHAR(30),
            shipping_method VARCHAR(20),
            subtotal DECIMAL(10,2),
            shipping_cost DECIMAL(10,2),
            tax DECIMAL(10,2),
            discount DECIMAL(10,2),
            total DECIMAL(10,2),
            currency VARCHAR(5),
            shipped_date TIMESTAMP,
            delivered_date TIMESTAMP,
            region VARCHAR(10),
            customer_segment VARCHAR(20)
        )
    """))
    
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id VARCHAR(20) PRIMARY KEY,
            order_id VARCHAR(20) REFERENCES orders(order_id),
            product_id VARCHAR(20) REFERENCES products(product_id),
            sku VARCHAR(20),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2),
            total_price DECIMAL(10,2),
            cost DECIMAL(10,2)
        )
    """))
    
    await session.commit()


async def insert_demo_data(session: AsyncSession):
    """Insert minimal demo data for tests."""
    # Insert test customers
    await session.execute(text("""
        INSERT INTO customers (customer_id, first_name, last_name, email, region, country, segment, created_at)
        VALUES 
            ('CUST_001', 'John', 'Doe', 'john@example.com', 'US', 'US', 'vip', '2024-01-01'),
            ('CUST_002', 'Jane', 'Smith', 'jane@example.com', 'UK', 'UK', 'regular', '2024-01-15'),
            ('CUST_003', 'Bob', 'Johnson', 'bob@example.com', 'EU', 'DE', 'new', '2024-02-01')
        ON CONFLICT DO NOTHING
    """))
    
    # Insert test products
    await session.execute(text("""
        INSERT INTO products (product_id, sku, name, category, base_price, cost, is_active, created_at)
        VALUES 
            ('PROD_001', 'SKU001', 'Widget A', 'Widgets', 29.99, 15.00, true, '2024-01-01'),
            ('PROD_002', 'SKU002', 'Widget B', 'Widgets', 49.99, 25.00, true, '2024-01-01'),
            ('PROD_003', 'SKU003', 'Gadget X', 'Gadgets', 99.99, 60.00, true, '2024-01-15')
        ON CONFLICT DO NOTHING
    """))
    
    # Insert test orders
    await session.execute(text("""
        INSERT INTO orders (order_id, customer_id, order_date, status, total, region, customer_segment)
        VALUES 
            ('ORD_001', 'CUST_001', '2024-01-10', 'completed', 79.98, 'US', 'vip'),
            ('ORD_002', 'CUST_001', '2024-01-15', 'completed', 149.97, 'US', 'vip'),
            ('ORD_003', 'CUST_002', '2024-01-20', 'completed', 49.99, 'UK', 'regular'),
            ('ORD_004', 'CUST_003', '2024-02-05', 'pending', 99.99, 'EU', 'new')
        ON CONFLICT DO NOTHING
    """))
    
    # Insert test order items
    await session.execute(text("""
        INSERT INTO order_items (order_item_id, order_id, product_id, sku, quantity, unit_price, total_price)
        VALUES 
            ('ITEM_001', 'ORD_001', 'PROD_001', 'SKU001', 2, 29.99, 59.98),
            ('ITEM_002', 'ORD_001', 'PROD_002', 'SKU002', 1, 49.99, 49.99),
            ('ITEM_003', 'ORD_002', 'PROD_003', 'SKU003', 1, 99.99, 99.99),
            ('ITEM_004', 'ORD_003', 'PROD_001', 'SKU001', 1, 29.99, 29.99),
            ('ITEM_005', 'ORD_004', 'PROD_002', 'SKU002', 2, 49.99, 99.98)
        ON CONFLICT DO NOTHING
    """))
    
    await session.commit()


@pytest_asyncio.fixture
async def demo_database(db_session):
    """Provide a database session with demo data loaded."""
    await setup_demo_tables(db_session)
    await insert_demo_data(db_session)
    yield db_session
