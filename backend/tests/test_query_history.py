"""
Unit tests for Query History Service (Build #3)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

# Add backend to path
import sys
sys.path.insert(0, '/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/backend')

from app.services.query_history import QueryHistoryService, QueryRecord


@pytest.fixture
def query_history_service():
    return QueryHistoryService()


@pytest.fixture
def sample_query():
    return "What is my total revenue for LBG?"


@pytest.fixture
def sample_embedding():
    return [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


class TestQueryHistoryService:
    """Test suite for QueryHistoryService"""
    
    def test_generate_id(self, query_history_service):
        """Test ID generation is unique"""
        id1 = query_history_service._generate_id()
        id2 = query_history_service._generate_id()
        
        assert id1 != id2
        assert len(id1) == 16
        assert len(id2) == 16
    
    def test_get_embedding(self, query_history_service, sample_query):
        """Test embedding generation"""
        embedding = asyncio.run(query_history_service._get_embedding(sample_query))
        
        assert len(embedding) == 10
        assert all(0 <= v <= 1 for v in embedding)
    
    def test_get_embedding_consistency(self, query_history_service, sample_query):
        """Test same query produces same embedding"""
        emb1 = asyncio.run(query_history_service._get_embedding(sample_query))
        emb2 = asyncio.run(query_history_service._get_embedding(sample_query))
        
        assert emb1 == emb2
    
    def test_get_embedding_different_queries(self, query_history_service):
        """Test different queries produce different embeddings"""
        emb1 = asyncio.run(query_history_service._get_embedding("revenue query"))
        emb2 = asyncio.run(query_history_service._get_embedding("customer query"))
        
        assert emb1 != emb2
    
    def test_cosine_similarity_identical(self, query_history_service, sample_embedding):
        """Test cosine similarity of identical vectors is 1"""
        similarity = query_history_service._cosine_similarity(sample_embedding, sample_embedding)
        
        assert similarity == 1.0
    
    def test_cosine_similarity_orthogonal(self, query_history_service):
        """Test cosine similarity of orthogonal vectors is 0"""
        v1 = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        v2 = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        
        similarity = query_history_service._cosine_similarity(v1, v2)
        
        assert similarity == 0.0
    
    def test_cosine_similarity_opposite(self, query_history_service):
        """Test cosine similarity of opposite vectors is -1"""
        v1 = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        v2 = [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        similarity = query_history_service._cosine_similarity(v1, v2)
        
        assert similarity == -1.0
    
    def test_cosine_similarity_zero_vector(self, query_history_service):
        """Test cosine similarity handles zero vector"""
        v1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        v2 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        similarity = query_history_service._cosine_similarity(v1, v2)
        
        assert similarity == 0.0


class TestQueryRecord:
    """Test QueryRecord dataclass"""
    
    def test_to_dict(self):
        """Test QueryRecord serialization"""
        record = QueryRecord(
            id="test123",
            query="test query",
            sql="SELECT * FROM test",
            result_summary="Test result",
            embedding=[0.1, 0.2],
            user_id="user1",
            tenant_id="tenant1",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            execution_time_ms=100,
            success=True
        )
        
        d = record.to_dict()
        
        assert d["id"] == "test123"
        assert d["query"] == "test query"
        assert d["sql"] == "SELECT * FROM test"
        assert d["user_id"] == "user1"
        assert d["created_at"] == "2024-01-01T12:00:00"


class TestQueryHistoryIntegration:
    """Integration tests with mocked database"""
    
    @pytest.mark.asyncio
    async def test_record_query(self, query_history_service, sample_query):
        """Test recording a query"""
        # Mock the database session
        mock_session = AsyncMock()
        
        with patch('app.services.query_history.AsyncSessionLocal') as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            record = await query_history_service.record_query(
                query=sample_query,
                user_id="user1",
                tenant_id="tenant1",
                sql="SELECT SUM(amount) FROM orders",
                result_summary="$1,101,327.94",
                execution_time_ms=150,
                success=True
            )
        
        assert record.query == sample_query
        assert record.user_id == "user1"
        assert record.tenant_id == "tenant1"
        assert record.sql == "SELECT SUM(amount) FROM orders"
        assert record.result_summary == "$1,101,327.94"
        assert record.execution_time_ms == 150
        assert record.success is True
        assert record.embedding is not None
        assert len(record.embedding) == 10
    
    @pytest.mark.asyncio
    async def test_search_similar_queries(self, query_history_service):
        """Test semantic search"""
        # Create mock records
        records = [
            QueryRecord(
                id="1",
                query="revenue this month",
                sql="SELECT...",
                result_summary="",
                embedding=await query_history_service._get_embedding("revenue this month"),
                user_id="user1",
                tenant_id="tenant1",
                created_at=datetime.utcnow(),
                execution_time_ms=100,
                success=True
            ),
            QueryRecord(
                id="2",
                query="customer count",
                sql="SELECT...",
                result_summary="",
                embedding=await query_history_service._get_embedding("customer count"),
                user_id="user1",
                tenant_id="tenant1",
                created_at=datetime.utcnow(),
                execution_time_ms=100,
                success=True
            )
        ]
        
        # Mock get_recent_queries to return these
        query_history_service.get_recent_queries = AsyncMock(return_value=records)
        
        # Search for revenue-related query
        results = await query_history_service.search_similar_queries(
            query="monthly revenue",
            user_id="user1",
            tenant_id="tenant1",
            limit=5
        )
        
        # Should find the revenue query
        assert len(results) > 0
        assert any("revenue" in r.query.lower() for r in results)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
