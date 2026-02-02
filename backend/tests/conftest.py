"""
Comprehensive pytest configuration for AI Analytics Platform tests.

This module provides:
- Database fixtures (SQLite for testing)
- Mock LLM provider fixtures
- Mock Redis/cache fixtures  
- FastAPI test client fixtures
- Sample data fixtures
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["MOONSHOT_API_KEY"] = "sk-test-moonshot"
os.environ["OPENAI_API_KEY"] = "sk-test-openai"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use DB 15 for tests
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"

# Patch ChatOpenAI before importing modules that use it
_mock_chatopenai_instances = []
_mock_response_content = '{"intent": "simple", "reasoning": "test"}'

class MockChatOpenAI:
    """Mock ChatOpenAI class for testing."""
    
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', 'gpt-4')
        self.temperature = kwargs.get('temperature', 0.1)
        self.api_key = kwargs.get('api_key', 'test-key')
        _mock_chatopenai_instances.append(self)
        # Store the mock responses that will be used
        self._mock_response = None
    
    def set_mock_response(self, content):
        """Set the mock response content."""
        self._mock_response = Mock()
        self._mock_response.content = content
    
    async def ainvoke(self, messages, **kwargs):
        """Mock async invoke."""
        global _mock_response_content
        if self._mock_response is None:
            self._mock_response = Mock()
            self._mock_response.content = _mock_response_content
        return self._mock_response
    
    async def astream(self, messages, **kwargs):
        """Mock async stream."""
        chunks = ['{', '"intent"', ': ', '"simple"', '}']
        for chunk in chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            yield mock_chunk


class MockOpenAIEmbeddings:
    """Mock OpenAIEmbeddings class for testing."""
    
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', 'text-embedding-3-small')
        self.api_key = kwargs.get('api_key', 'test-key')
    
    async def aembed_query(self, query: str) -> list:
        """Mock embedding generation - returns a fixed vector."""
        # Return a 1536-dimensional zero vector (standard OpenAI embedding size)
        return [0.0] * 1536
    
    async def aembed_documents(self, documents: list) -> list:
        """Mock document embedding."""
        return [[0.0] * 1536 for _ in documents]


# Apply patches before importing app modules
patch('langchain_openai.ChatOpenAI', MockChatOpenAI).start()
patch('langchain_openai.OpenAIEmbeddings', MockOpenAIEmbeddings).start()

# Now import app modules
from app.main import app
from app.config import get_settings, Settings
from app.agent.state import AgentState


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings for testing with SQLite database."""
    settings = Settings(
        database_url="sqlite+aiosqlite:///./test.db",
        moonshot_api_key="sk-test-moonshot",
        openai_api_key="sk-test-openai",
        redis_url="redis://localhost:6379/15",
        environment="testing",
        debug=True,
        secret_key="test-secret-key-for-testing-only",
        jwt_secret_key="test-jwt-secret-key",
        supabase_url="http://localhost:54321",
        supabase_service_key="test-service-key",
    )
    return settings


@pytest.fixture(autouse=True)
def patch_settings(mock_settings):
    """Automatically patch settings for all tests."""
    with patch("app.config.get_settings", return_value=mock_settings):
        yield mock_settings


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def db_engine():
    """Create a database engine for testing."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test.db",
        echo=False,
        future=True,
    )
    
    # Create tables using a new event loop
    from app.database_legacy import Base
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(setup())
    loop.close()
    
    yield engine
    
    # Cleanup
    async def teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(teardown())
    loop.close()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a database session for testing."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    
    async_session = async_sessionmaker(
        db_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def demo_database(db_session):
    """Create a demo database with sample data for testing."""
    from sqlalchemy import text
    
    # Create demo tables
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            segment TEXT,
            created_at TEXT
        )
    """))
    
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            created_at TEXT
        )
    """))
    
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            total REAL,
            status TEXT,
            order_date TEXT
        )
    """))
    
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL
        )
    """))
    
    # Insert sample data
    await db_session.execute(text("""
        INSERT INTO customers (customer_id, first_name, last_name, email, segment, created_at)
        VALUES 
            (1, 'John', 'Doe', 'john@example.com', 'vip', '2024-01-01'),
            (2, 'Jane', 'Smith', 'jane@example.com', 'regular', '2024-01-15'),
            (3, 'Bob', 'Wilson', 'bob@example.com', 'new', '2024-02-01')
    """))
    
    await db_session.execute(text("""
        INSERT INTO products (product_id, name, category, price, created_at)
        VALUES 
            (1, 'Widget A', 'widgets', 29.99, '2024-01-01'),
            (2, 'Widget B', 'widgets', 49.99, '2024-01-01'),
            (3, 'Gadget X', 'gadgets', 99.99, '2024-01-15')
    """))
    
    await db_session.execute(text("""
        INSERT INTO orders (order_id, customer_id, total, status, order_date)
        VALUES 
            (1, 1, 129.98, 'completed', '2024-01-10'),
            (2, 1, 49.99, 'completed', '2024-01-20'),
            (3, 2, 99.99, 'pending', '2024-02-05'),
            (4, 3, 29.99, 'completed', '2024-02-10')
    """))
    
    await db_session.execute(text("""
        INSERT INTO order_items (item_id, order_id, product_id, quantity, price)
        VALUES 
            (1, 1, 1, 2, 29.99),
            (2, 1, 2, 1, 49.99),
            (3, 2, 2, 1, 49.99),
            (4, 3, 3, 1, 99.99),
            (5, 4, 1, 1, 29.99)
    """))
    
    await db_session.commit()
    
    yield db_session
    
    # Cleanup
    await db_session.execute(text("DROP TABLE IF EXISTS order_items"))
    await db_session.execute(text("DROP TABLE IF EXISTS orders"))
    await db_session.execute(text("DROP TABLE IF EXISTS products"))
    await db_session.execute(text("DROP TABLE IF EXISTS customers"))
    await db_session.commit()


# =============================================================================
# Mock LLM Provider Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_provider():
    """Provide a mock LLM provider for testing."""
    mock = AsyncMock()
    
    # Default return values
    mock.generate = AsyncMock(return_value=json.dumps({
        "intent": "simple",
        "reasoning": "Direct lookup query"
    }))
    
    mock.generate_json = AsyncMock(return_value={
        "sql": "SELECT * FROM orders LIMIT 10",
        "explanation": "Retrieve orders data",
        "chart_type": "table",
        "confidence": 0.95
    })
    
    mock.stream = AsyncMock(return_value=async_generator([
        "SELECT ", "* ", "FROM ", "orders"
    ]))
    
    return mock


async def async_generator(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item


@pytest.fixture(autouse=True)
def patch_llm_provider(mock_llm_provider):
    """Automatically patch LLM provider for all tests."""
    from app.agent.nodes import classify, analyze, error
    
    # Create a mock LLM that can be controlled per-test
    class ControllableMockLLM:
        def __init__(self):
            self._response_content = '{"intent": "simple", "reasoning": "test"}'
        
        def set_response(self, content):
            self._response_content = content
        
        async def ainvoke(self, messages, **kwargs):
            mock_response = Mock()
            mock_response.content = self._response_content
            return mock_response
        
        async def astream(self, messages, **kwargs):
            chunks = ['{', '"intent"', ': ', '"simple"', '}']
            for chunk in chunks:
                mock_chunk = Mock()
                mock_chunk.content = chunk
                yield mock_chunk
    
    # Create controllable mock
    controllable_mock = ControllableMockLLM()
    
    # Attach set_response to mock_llm_provider for tests to use
    mock_llm_provider.set_chatopenai_response = controllable_mock.set_response
    
    # Patch the LLM provider module
    with patch("app.llm_provider.get_llm_provider", return_value=mock_llm_provider):
        # Patch in generate module which uses llm_provider
        with patch("app.agent.nodes.generate.llm_provider", mock_llm_provider):
            # Patch the module-level llm instances in classify, analyze, error nodes
            with patch.object(classify, "llm", controllable_mock):
                with patch.object(analyze, "llm", controllable_mock):
                    with patch.object(error, "llm", controllable_mock):
                        yield mock_llm_provider


# =============================================================================
# Mock Redis/Cache Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Provide a mock Redis client for testing."""
    mock = AsyncMock()
    
    # Mock storage
    mock._storage = {}
    
    async def mock_get(key):
        return mock._storage.get(key)
    
    async def mock_setex(key, ttl, value):
        mock._storage[key] = value
        return True
    
    async def mock_delete(key):
        if key in mock._storage:
            del mock._storage[key]
        return True
    
    async def mock_exists(key):
        return 1 if key in mock._storage else 0
    
    mock.get = mock_get
    mock.setex = mock_setex
    mock.delete = mock_delete
    mock.exists = mock_exists
    
    return mock


@pytest.fixture(autouse=True)
def patch_redis(mock_redis):
    """Automatically patch Redis for all tests."""
    with patch("app.cache.redis_client", mock_redis):
        with patch("app.cache.get_enhanced_cache") as mock_cache:
            cache_instance = AsyncMock()
            cache_instance._get_redis = AsyncMock(return_value=mock_redis)
            cache_instance.get = AsyncMock(return_value=None)
            cache_instance.set = AsyncMock(return_value=True)
            mock_cache.return_value = cache_instance
            yield mock_redis


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture
def client(mock_settings, mock_redis, mock_llm_provider):
    """Provide a synchronous TestClient for testing."""
    from fastapi.testclient import TestClient
    
    with patch("app.config.get_settings", return_value=mock_settings):
        with patch("app.cache.redis_client", mock_redis):
            with patch("app.llm_provider.get_llm_provider", return_value=mock_llm_provider):
                with patch("app.main.init_db", AsyncMock()):
                    with patch("app.async_jobs.start_background_worker", AsyncMock()):
                        with patch("app.async_jobs.stop_background_worker", AsyncMock()):
                            with TestClient(app) as test_client:
                                yield test_client


@pytest_asyncio.fixture
async def async_client(mock_settings, mock_redis, mock_llm_provider):
    """Provide an async HTTP client for testing."""
    with patch("app.config.get_settings", return_value=mock_settings):
        with patch("app.cache.redis_client", mock_redis):
            with patch("app.llm_provider.get_llm_provider", return_value=mock_llm_provider):
                with patch("app.main.init_db", AsyncMock()):
                    with patch("app.async_jobs.start_background_worker", AsyncMock()):
                        with patch("app.async_jobs.stop_background_worker", AsyncMock()):
                            async with AsyncClient(
                                transport=ASGITransport(app=app),
                                base_url="http://test"
                            ) as ac:
                                yield ac


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing."""
    return AgentState(
        query="What was revenue last month?",
        tenant_id="test-tenant",
        user_id="test-user",
        workflow_id="test-workflow-123",
        connection_id=None,
        investigation_history=[],
        retry_count=0,
        sql_valid=True,
        needs_clarification=False,
        investigation_complete=False,
        current_step="classify_intent",
        step_status="pending",
        step_message="",
    )


@pytest.fixture
def sample_query_request():
    """Sample query request for testing."""
    return {
        "query": "What was revenue last month?",
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "connection_id": None
    }


@pytest.fixture
def sample_dashboard_create():
    """Sample dashboard create data for testing."""
    return {
        "name": "Sales Dashboard",
        "description": "Overview of sales metrics",
        "tenant_id": "test-tenant",
        "user_id": "test-user"
    }


@pytest.fixture
def sample_connection_config():
    """Sample database connection config for testing."""
    return {
        "name": "Test Database",
        "db_type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "test",
        "username": "test_user",
        "password": "test_pass"
    }


@pytest.fixture
def sample_db_config():
    """Sample database config object for testing."""
    from app.database.connector import DatabaseConfig, DatabaseType
    
    return DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test",
        username="test",
        password="test"
    )


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "SELECT SUM(amount) as revenue FROM orders WHERE created_at >= date('now', 'start of month', '-1 month')",
        "role": "assistant"
    }


# =============================================================================
# Additional Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    mock = AsyncMock()
    mock.log_query = AsyncMock(return_value=True)
    mock.log_export = AsyncMock(return_value=True)
    return mock


@pytest.fixture(autouse=True)
def patch_audit_logger(mock_audit_logger):
    """Automatically patch audit logger for all tests."""
    with patch("app.security.get_audit_logger", return_value=mock_audit_logger):
        yield mock_audit_logger


@pytest.fixture
def mock_monitor():
    """Mock monitoring for testing."""
    mock = MagicMock()
    mock.get_stats = Mock(return_value={"total": 0, "success": 0})
    mock.get_llm_stats = Mock(return_value={"calls": 0, "tokens": 0})
    mock.get_error_stats = Mock(return_value={"count": 0})
    return mock


@pytest.fixture(autouse=True)
def patch_monitor(mock_monitor):
    """Automatically patch monitor for all tests."""
    with patch("app.monitoring.get_monitor", return_value=mock_monitor):
        yield mock_monitor


@pytest.fixture
def mock_job_queue():
    """Mock job queue for testing."""
    mock = MagicMock()
    mock.get_queue_status = Mock(return_value={"pending": 0, "processing": 0})
    mock.get_job = Mock(return_value=None)
    mock.enqueue = AsyncMock(return_value="job-123")
    return mock


@pytest.fixture(autouse=True)
def patch_job_queue(mock_job_queue):
    """Automatically patch job queue for all tests."""
    with patch("app.async_jobs.get_job_queue", return_value=mock_job_queue):
        yield mock_job_queue


# =============================================================================
# Export Manager Mock
# =============================================================================

@pytest.fixture
def mock_export_manager():
    """Mock export manager for testing."""
    mock = AsyncMock()
    mock.export = AsyncMock(return_value={
        "content": b"test,data\n1,2",
        "content_type": "text/csv",
        "filename": "export.csv"
    })
    return mock


@pytest.fixture(autouse=True)
def patch_export_manager(mock_export_manager):
    """Automatically patch export manager for all tests."""
    with patch("app.export.ExportManager", return_value=mock_export_manager):
        yield mock_export_manager
