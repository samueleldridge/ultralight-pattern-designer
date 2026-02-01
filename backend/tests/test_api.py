"""
Unit and integration tests for API endpoints.

Tests cover:
- Query endpoints (POST /api/query, GET /api/stream/{workflow_id})
- Dashboard endpoints (CRUD operations)
- Suggestions endpoints
- Connection endpoints
- Health check
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import status


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    """Test health and root endpoints."""
    
    def test_health_check(self, client):
        """Health check should return healthy status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client):
        """Health check should work with async client."""
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"


# =============================================================================
# Query Endpoint Tests
# =============================================================================

@pytest.mark.api
class TestQueryEndpoints:
    """Test query workflow endpoints."""
    
    def test_start_query_success(self, client, sample_query_request):
        """Starting a query should return workflow ID."""
        response = client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "started"
        assert "stream" in data["message"].lower()
    
    def test_start_query_missing_required_fields(self, client):
        """Query without required fields should fail validation."""
        # Missing query field
        response = client.post("/api/query", json={
            "tenant_id": "tenant-123",
            "user_id": "user-456"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_start_query_optional_connection_id(self, client):
        """Query should work without optional connection_id."""
        response = client.post("/api/query", json={
            "query": "Test query",
            "tenant_id": "tenant-123",
            "user_id": "user-456"
        })
        assert response.status_code == status.HTTP_200_OK
        assert "workflow_id" in response.json()
    
    @pytest.mark.asyncio
    async def test_stream_workflow_not_found(self, async_client):
        """Streaming non-existent workflow should return error."""
        response = await async_client.get(
            "/api/stream/non-existent-workflow",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        # SSE stream returns 200 even for errors, error is in the stream
        content = response.text
        assert "error" in content.lower() or "Workflow not found" in content
    
    @pytest.mark.asyncio
    async def test_stream_workflow_success(self, async_client, mock_redis):
        """Streaming existing workflow should yield events."""
        # Setup mock state
        workflow_id = "test-workflow-123"
        mock_state = {
            "query": "Test query",
            "tenant_id": "t1",
            "user_id": "u1",
            "workflow_id": workflow_id,
            "started_at": datetime.utcnow().isoformat(),
            "investigation_history": [],
            "retry_count": 0,
            "sql_valid": True,
            "needs_clarification": False,
            "investigation_complete": False
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(mock_state))
        
        response = await async_client.get(
            f"/api/stream/{workflow_id}",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers.get("content-type", "")
    
    def test_get_workflow_result_not_implemented(self, client):
        """Getting workflow result should return not implemented status."""
        response = client.get("/api/workflow/test-workflow/result")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["workflow_id"] == "test-workflow"
        assert data["status"] == "not_implemented"


# =============================================================================
# Dashboard Endpoint Tests
# =============================================================================

@pytest.mark.api
class TestDashboardEndpoints:
    """Test dashboard CRUD endpoints."""
    
    def test_list_dashboards(self, client):
        """Listing dashboards should return list."""
        response = client.get("/api/dashboards")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_dashboard_success(self, client, sample_dashboard_create):
        """Creating dashboard should return dashboard data."""
        response = client.post("/api/dashboards", json=sample_dashboard_create)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_dashboard_create["name"]
    
    def test_create_dashboard_missing_name(self, client):
        """Creating dashboard without name should fail."""
        response = client.post("/api/dashboards", json={
            "description": "Dashboard without name"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_list_views(self, client):
        """Listing views for a dashboard should return list."""
        response = client.get("/api/dashboards/dashboard-123/views")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_view_success(self, client):
        """Creating a view should return view data."""
        view_data = {
            "dashboard_id": "dashboard-123",
            "title": "Revenue Chart",
            "query_text": "SELECT * FROM revenue",
            "position_x": 0,
            "position_y": 0,
            "width": 6,
            "height": 4,
            "chart_type": "line"
        }
        
        response = client.post("/api/dashboards/views", json=view_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert data["title"] == view_data["title"]
    
    def test_create_view_invalid_position(self, client):
        """Creating view with invalid position should fail."""
        response = client.post("/api/dashboards/views", json={
            "title": "Test View",
            "query_text": "SELECT 1",
            "position_x": -1,  # Invalid negative position
            "position_y": 0,
            "width": 6,
            "height": 4
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Suggestions Endpoint Tests
# =============================================================================

@pytest.mark.api
class TestSuggestionsEndpoints:
    """Test suggestions endpoints."""
    
    def test_get_suggestions(self, client):
        """Getting suggestions should return list of suggestions."""
        response = client.get("/api/suggestions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            suggestion = data[0]
            assert "type" in suggestion
            assert "text" in suggestion
            assert "action" in suggestion
            assert "query" in suggestion
    
    def test_get_suggestions_structure(self, client):
        """Suggestions should have correct structure."""
        response = client.get("/api/suggestions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        for suggestion in data:
            assert isinstance(suggestion.get("type"), str)
            assert isinstance(suggestion.get("text"), str)
            assert isinstance(suggestion.get("action"), str)
            assert isinstance(suggestion.get("query"), str)
    
    def test_search_history(self, client):
        """Searching history should return results."""
        response = client.get("/api/suggestions/history/search?q=revenue")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_search_history_empty_query(self, client):
        """Searching with empty query should return empty results."""
        response = client.get("/api/suggestions/history/search?q=")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


# =============================================================================
# Connection Endpoint Tests
# =============================================================================

@pytest.mark.api
class TestConnectionEndpoints:
    """Test database connection endpoints."""
    
    def test_list_connections(self, client):
        """Listing connections should return list."""
        response = client.get("/api/connections")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_connection(self, client, sample_connection_config):
        """Creating connection should return connection data."""
        response = client.post("/api/connections", json=sample_connection_config)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert data["status"] == "created"
    
    def test_test_connection(self, client):
        """Testing connection should return status."""
        response = client.post("/api/connections/conn-123/test")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
    
    def test_sync_schema(self, client):
        """Syncing schema should return syncing status."""
        response = client.post("/api/connections/conn-123/sync-schema")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "syncing"


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_404_not_found(self, client):
        """Non-existent endpoints should return 404."""
        response = client.get("/api/non-existent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_invalid_json_payload(self, client):
        """Invalid JSON payload should return 422."""
        response = client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_method_not_allowed(self, client):
        """Wrong HTTP method should return 405."""
        response = client.delete("/api/query")  # DELETE not allowed
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# =============================================================================
# CORS Tests
# =============================================================================

@pytest.mark.api
class TestCORSMiddleware:
    """Test CORS middleware configuration."""
    
    def test_cors_preflight(self, client):
        """CORS preflight requests should be handled."""
        response = client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_headers_present(self, client):
        """CORS headers should be present in responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestQueryIntegration:
    """Integration tests for query workflow."""
    
    @pytest.mark.asyncio
    async def test_full_query_workflow(self, async_client, mock_redis, mock_llm_provider):
        """Test complete query workflow from start to stream."""
        # Mock LLM response
        mock_llm_provider.generate_json.return_value = {
            "sql": "SELECT * FROM orders",
            "explanation": "Get all orders",
            "chart_type": "table",
            "confidence": 0.95
        }
        
        # 1. Start query
        start_response = await async_client.post("/api/query", json={
            "query": "Show me all orders",
            "tenant_id": "test-tenant",
            "user_id": "test-user"
        })
        
        assert start_response.status_code == status.HTTP_200_OK
        workflow_id = start_response.json()["workflow_id"]
        
        # 2. Setup mock workflow state
        mock_state = {
            "query": "Show me all orders",
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "workflow_id": workflow_id,
            "started_at": datetime.utcnow().isoformat(),
            "investigation_history": [],
            "retry_count": 0,
            "sql_valid": True,
            "needs_clarification": False,
            "investigation_complete": False
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(mock_state))
        
        # 3. Stream workflow
        stream_response = await async_client.get(
            f"/api/stream/{workflow_id}",
            headers={"Accept": "text/event-stream"}
        )
        
        assert stream_response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in stream_response.headers.get("content-type", "")
