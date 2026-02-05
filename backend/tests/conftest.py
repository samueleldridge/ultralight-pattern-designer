"""
Pytest configuration and shared fixtures
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_user():
    """Sample user fixture"""
    return {
        "id": "user123",
        "tenant_id": "tenant456",
        "email": "test@example.com"
    }


@pytest.fixture
def sample_tenant():
    """Sample tenant fixture"""
    return {
        "id": "tenant456",
        "name": "Test Corp"
    }


@pytest.fixture
def mock_async_session_local(mock_db_session):
    """Mock AsyncSessionLocal context manager"""
    async def mock_context(*args, **kwargs):
        return mock_db_session
    
    return mock_context
