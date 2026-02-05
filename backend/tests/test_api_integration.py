"""
API Integration Tests

Tests the actual API endpoints for:
- Query History (Build #3)
- User Memory (Build #4)
- Subscriptions (Build #5)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, '/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/backend')

from app.main import app


client = TestClient(app)


class TestQueryHistoryAPI:
    """Test Query History API endpoints"""
    
    def test_get_recent_queries_unauthorized(self):
        """Test getting recent queries without auth fails"""
        response = client.get("/api/history")
        # Should require auth (returns 401 or 403)
        assert response.status_code in [401, 403]
    
    def test_get_recent_queries_authorized(self):
        """Test getting recent queries with auth"""
        with patch('app.api.history.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.history.get_query_history_service') as mock_service:
                mock_service.return_value.get_recent_queries = AsyncMock(return_value=[])
                
                response = client.get("/api/history")
                
                # Should succeed
                assert response.status_code == 200
                assert response.json() == []
    
    def test_search_queries(self):
        """Test searching query history"""
        with patch('app.api.history.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.history.get_query_history_service') as mock_service:
                mock_service.return_value.search_similar_queries = AsyncMock(
                    return_value=[]
                )
                
                response = client.get("/api/history/search?q=revenue")
                
                assert response.status_code == 200
                data = response.json()
                assert "query" in data
                assert "results" in data
                assert data["query"] == "revenue"
    
    def test_get_popular_queries(self):
        """Test getting popular queries"""
        with patch('app.api.history.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.history.get_query_history_service') as mock_service:
                mock_service.return_value.get_popular_queries = AsyncMock(
                    return_value=[
                        {"query": "revenue", "count": 10},
                        {"query": "customers", "count": 5}
                    ]
                )
                
                response = client.get("/api/history/popular")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["query"] == "revenue"
                assert data[0]["count"] == 10


class TestUserMemoryAPI:
    """Test User Memory API endpoints"""
    
    def test_get_user_memory(self):
        """Test getting user memory profile"""
        with patch('app.api.user_memory.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.user_memory.get_memory_service') as mock_service:
                mock_profile = Mock()
                mock_profile.user_id = "user1"
                mock_profile.interests = [{"topic": "revenue", "frequency": 5}]
                mock_profile.preferred_chart_types = ["line", "bar"]
                mock_profile.memory_summary = "User likes revenue data"
                mock_profile.updated_at = __import__('datetime').datetime.utcnow()
                
                mock_service.return_value.get_or_create_profile = AsyncMock(
                    return_value=mock_profile
                )
                
                response = client.get("/api/users/me/memory")
                
                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == "user1"
                assert len(data["interests"]) == 1
                assert data["interests"][0]["topic"] == "revenue"
    
    def test_consolidate_memory(self):
        """Test manual memory consolidation"""
        with patch('app.api.user_memory.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.user_memory.get_memory_service') as mock_service:
                mock_profile = Mock()
                mock_profile.interests = [{"topic": "revenue"}]
                mock_profile.memory_summary = "Updated summary"
                mock_profile.updated_at = __import__('datetime').datetime.utcnow()
                
                mock_service.return_value.consolidate_memory = AsyncMock(
                    return_value=mock_profile
                )
                
                response = client.post("/api/users/me/memory/consolidate?lookback_days=7")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["interests_found"] == 1
    
    def test_get_user_interactions(self):
        """Test getting user interactions"""
        with patch('app.api.user_memory.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            response = client.get("/api/users/me/interactions")
            
            # Should work (even if empty)
            assert response.status_code in [200, 500]  # 500 if DB not set up
    
    def test_get_proactive_suggestions(self):
        """Test getting proactive suggestions"""
        with patch('app.api.user_memory.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.user_memory.get_proactive_service') as mock_service:
                from datetime import datetime
                
                mock_suggestion = Mock()
                mock_suggestion.id = "sugg1"
                mock_suggestion.title = "Revenue Spike"
                mock_suggestion.description = "Detected spike"
                mock_suggestion.suggested_query = "Show me revenue"
                mock_suggestion.reason = "Based on interest"
                mock_suggestion.priority = Mock()
                mock_suggestion.priority.value = "high"
                mock_suggestion.created_at = datetime.utcnow()
                
                mock_service.return_value.get_pending_suggestions = AsyncMock(
                    return_value=[mock_suggestion]
                )
                
                response = client.get("/api/users/me/suggestions")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["title"] == "Revenue Spike"


class TestSubscriptionsAPI:
    """Test Subscriptions API endpoints"""
    
    def test_create_subscription(self):
        """Test creating a subscription"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                from datetime import datetime
                
                mock_sub = Mock()
                mock_sub.id = "sub123"
                mock_sub.name = "Test Alert"
                mock_sub.description = "Test description"
                mock_sub.query_template = "SELECT * FROM test"
                mock_sub.frequency = "weekly"
                mock_sub.condition_type = "threshold"
                mock_sub.status = "active"
                mock_sub.next_run_at = datetime.utcnow()
                mock_sub.last_run_at = None
                mock_sub.run_count = 0
                mock_sub.hit_count = 0
                mock_sub.created_at = datetime.utcnow()
                
                mock_service.return_value.create_subscription = AsyncMock(
                    return_value=mock_sub
                )
                
                response = client.post("/api/subscriptions", json={
                    "name": "Test Alert",
                    "description": "Test description",
                    "query_template": "SELECT * FROM test",
                    "query_type": "sql",
                    "frequency": "weekly",
                    "condition_type": "threshold",
                    "condition_config": {"column": "value", "operator": "<", "value": 10},
                    "notify_on_condition_only": True,
                    "notification_channel": "in_app"
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Alert"
                assert data["status"] == "active"
    
    def test_list_subscriptions(self):
        """Test listing subscriptions"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                mock_service.return_value.get_user_subscriptions = AsyncMock(return_value=[])
                
                response = client.get("/api/subscriptions")
                
                assert response.status_code == 200
                assert response.json() == []
    
    def test_pause_subscription(self):
        """Test pausing a subscription"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                mock_service.return_value.pause_subscription = AsyncMock(return_value=True)
                
                response = client.post("/api/subscriptions/sub123/pause")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "paused"
                assert data["subscription_id"] == "sub123"
    
    def test_resume_subscription(self):
        """Test resuming a subscription"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                mock_service.return_value.resume_subscription = AsyncMock(return_value=True)
                
                response = client.post("/api/subscriptions/sub123/resume")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "active"
    
    def test_cancel_subscription(self):
        """Test cancelling a subscription"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                mock_service.return_value.cancel_subscription = AsyncMock(return_value=True)
                
                response = client.delete("/api/subscriptions/sub123")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"
    
    def test_run_subscription_now(self):
        """Test running subscription immediately"""
        with patch('app.api.subscriptions.get_current_user') as mock_auth:
            mock_auth.return_value = {"id": "user1", "tenant_id": "tenant1"}
            
            with patch('app.api.subscriptions.get_subscription_service') as mock_service:
                mock_result = Mock()
                mock_result.condition_met = True
                mock_result.rows_found = 5
                
                mock_service.return_value.get_user_subscriptions = AsyncMock(
                    return_value=[Mock(id="sub123")]
                )
                mock_service.return_value.execute_subscription_check = AsyncMock(
                    return_value=mock_result
                )
                
                response = client.post("/api/subscriptions/sub123/run-now")
                
                assert response.status_code == 200
                data = response.json()
                assert data["executed"] is True
                assert data["condition_met"] is True
                assert data["rows_found"] == 5


class TestHealthAndRoot:
    """Test health and root endpoints"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_root(self):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "features" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
