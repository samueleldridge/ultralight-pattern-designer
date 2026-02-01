"""
Pytest configuration - simplified for reliability.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = get_settings()
    settings.database_url = "sqlite+aiosqlite:///./test.db"
    settings.moonshot_api_key = "sk-test"
    settings.openai_api_key = "sk-test"
    return settings


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for testing"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing"""
    return {
        "question": "What was revenue last month?",
        "current_step": "classify",
        "sql": None,
        "results": None,
        "error": None,
        "visualization": None,
        "step_status": "pending",
        "step_message": "",
        "conversation_id": "test-123",
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return {
        "content": "SELECT SUM(amount) as revenue FROM orders WHERE created_at >= date('now', 'start of month', '-1 month')",
        "role": "assistant"
    }
