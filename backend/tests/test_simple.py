"""
Simple API tests that work with current setup.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health endpoint returns healthy status."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns API info."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "name" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_api_suggestions():
    """Test suggestions endpoint returns data."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Try the autocomplete endpoint which should exist
        response = await client.get("/api/suggestions/autocomplete?q=revenue")
        assert response.status_code == 200
        data = response.json()
        # Response is a dict with 'query' and 'suggestions' keys
        assert "suggestions" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_api_dashboards():
    """Test dashboards endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/dashboards")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_connections():
    """Test connections endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/connections")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_docs_endpoint():
    """Test Swagger docs are accessible."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
