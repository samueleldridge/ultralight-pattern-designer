"""
Unit tests for User Memory & Proactive Intelligence (Build #4)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, '/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/backend')

from app.intelligence.user_memory import (
    InterestDetectionService,
    UserMemoryService,
    UserProfile,
    UserInteraction,
    ProactiveIntelligenceService,
    SubscriptionConditionType,
    ProactivePriority,
    InterestCategory
)


class TestInterestDetectionService:
    """Test suite for InterestDetectionService"""
    
    @pytest.fixture
    def detector(self):
        return InterestDetectionService()
    
    def test_detect_themes_revenue_metrics(self, detector):
        """Test detecting revenue + metrics theme"""
        query = "What is my total revenue this month?"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "metrics" in theme_values
        assert "revenue" in theme_values
    
    def test_detect_themes_trend(self, detector):
        """Test detecting trend theme"""
        query = "Show me revenue trend over time"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "trends" in theme_values
    
    def test_detect_themes_comparison(self, detector):
        """Test detecting comparison theme"""
        query = "Compare this month vs last month"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "comparisons" in theme_values
    
    def test_detect_themes_anomaly(self, detector):
        """Test detecting anomaly theme"""
        query = "Are there any unusual spikes in revenue?"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "anomalies" in theme_values
    
    def test_detect_themes_prediction(self, detector):
        """Test detecting prediction theme"""
        query = "What will revenue be next month?"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "predictions" in theme_values
    
    def test_detect_themes_multiple_entities(self, detector):
        """Test detecting multiple entities"""
        query = "Show me revenue and customer churn"
        themes = detector.detect_themes(query)
        
        theme_values = [t["value"] for t in themes]
        assert "revenue" in theme_values
        assert "churn" in theme_values
    
    def test_normalize_query(self, detector):
        """Test query normalization"""
        query = "  WHAT   is   My  REVENUE???  "
        normalized = detector.normalize_query(query)
        
        assert normalized == "what is my revenue???"
    
    def test_normalize_query_lowercase(self, detector):
        """Test normalization produces lowercase"""
        query = "SELECT * FROM Revenue"
        normalized = detector.normalize_query(query)
        
        assert normalized == "select * from revenue"


class TestUserMemoryService:
    """Test suite for UserMemoryService"""
    
    @pytest.fixture
    def memory_service(self):
        return UserMemoryService()
    
    def test_generate_id(self, memory_service):
        """Test ID generation"""
        id1 = memory_service._generate_id()
        id2 = memory_service._generate_id()
        
        assert id1 != id2
        assert len(id1) == 16
    
    def test_categorize_theme_metrics(self, memory_service):
        """Test theme categorization for metrics"""
        category = memory_service._categorize_theme("metrics")
        assert category == "metrics"
    
    def test_categorize_theme_custom(self, memory_service):
        """Test theme categorization for custom entity"""
        category = memory_service._categorize_theme("revenue")
        assert category == "entity"
    
    @pytest.mark.asyncio
    async def test_record_interaction(self, memory_service):
        """Test recording user interaction"""
        with patch('app.intelligence.user_memory.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            interaction = await memory_service.record_interaction(
                user_id="user1",
                tenant_id="tenant1",
                query="What is my total revenue?",
                sql="SELECT SUM(amount) FROM orders",
                response_summary="$1M revenue",
                chart_type="metric",
                execution_time_ms=100,
                row_count=1
            )
        
        assert interaction.user_id == "user1"
        assert interaction.tenant_id == "tenant1"
        assert "revenue" in interaction.themes
        assert "revenue" in interaction.entities_mentioned
        assert interaction.sql == "SELECT SUM(amount) FROM orders"
        assert interaction.chart_type == "metric"
    
    @pytest.mark.asyncio
    async def test_record_interaction_detects_themes(self, memory_service):
        """Test interaction records detected themes"""
        with patch('app.intelligence.user_memory.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            interaction = await memory_service.record_interaction(
                user_id="user1",
                tenant_id="tenant1",
                query="Show me revenue trends over time"
            )
        
        assert "trends" in interaction.themes
        assert "revenue" in interaction.entities_mentioned


class TestProactiveIntelligenceService:
    """Test suite for ProactiveIntelligenceService"""
    
    @pytest.fixture
    def proactive_service(self):
        mock_db = Mock()
        mock_llm = Mock()
        return ProactiveIntelligenceService(mock_db, mock_llm)
    
    def test_generate_id(self, proactive_service):
        """Test ID generation"""
        id1 = proactive_service._generate_id()
        id2 = proactive_service._generate_id()
        
        assert id1 != id2
        assert len(id1) == 16
    
    @pytest.mark.asyncio
    async def test_check_for_anomalies_revenue(self, proactive_service):
        """Test anomaly detection for revenue"""
        from app.intelligence.user_memory import UserProfile
        
        profile = Mock()
        profile.interests = [{"topic": "revenue", "category": "entity"}]
        
        suggestions = await proactive_service._check_for_anomalies(
            user_id="user1",
            tenant_id="tenant1",
            topic="revenue",
            profile=profile
        )
        
        assert len(suggestions) > 0
        assert any("Revenue" in s.title for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_check_for_trends_customers(self, proactive_service):
        """Test trend detection for customers"""
        from app.intelligence.user_memory import UserProfile
        
        profile = Mock()
        profile.interests = [{"topic": "customers", "category": "entity"}]
        
        suggestions = await proactive_service._check_for_trends(
            user_id="user1",
            tenant_id="tenant1",
            topic="customers",
            profile=profile
        )
        
        assert len(suggestions) > 0
        assert any("Customer" in s.title for s in suggestions)


class TestInterestCategories:
    """Test InterestCategory enum"""
    
    def test_category_values(self):
        """Test category enum values"""
        assert InterestCategory.METRICS.value == "metrics"
        assert InterestCategory.TRENDS.value == "trends"
        assert InterestCategory.COMPARISONS.value == "comparisons"
        assert InterestCategory.SEGMENTS.value == "segments"
        assert InterestCategory.ANOMALIES.value == "anomalies"
        assert InterestCategory.PREDICTIONS.value == "predictions"


class TestProactivePriority:
    """Test ProactivePriority enum"""
    
    def test_priority_values(self):
        """Test priority enum values"""
        assert ProactivePriority.LOW.value == "low"
        assert ProactivePriority.MEDIUM.value == "medium"
        assert ProactivePriority.HIGH.value == "high"
        assert ProactivePriority.URGENT.value == "urgent"


class TestUserInterestDataclass:
    """Test UserInterest dataclass"""
    
    def test_to_dict(self):
        """Test UserInterest serialization"""
        from app.intelligence.user_memory import UserInterest
        
        interest = UserInterest(
            topic="revenue",
            category=InterestCategory.METRICS,
            frequency=5,
            last_asked=datetime(2024, 1, 1, 12, 0, 0),
            confidence=0.9,
            related_entities=["sales", "income"]
        )
        
        d = interest.to_dict()
        
        assert d["topic"] == "revenue"
        assert d["category"] == "metrics"
        assert d["frequency"] == 5
        assert d["confidence"] == 0.9
        assert d["related_entities"] == ["sales", "income"]


class TestIntegrationScenarios:
    """End-to-end integration test scenarios"""
    
    @pytest.mark.asyncio
    async def test_user_asks_about_revenue_multiple_times(self):
        """Test user repeatedly asking about revenue builds memory"""
        memory_service = UserMemoryService()
        
        # Simulate multiple revenue queries
        queries = [
            "What is my revenue?",
            "Show me revenue this month",
            "Total revenue by product",
            "Revenue trend over time"
        ]
        
        with patch('app.intelligence.user_memory.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            for query in queries:
                await memory_service.record_interaction(
                    user_id="user1",
                    tenant_id="tenant1",
                    query=query
                )
        
        # Verify themes would be detected
        detector = InterestDetectionService()
        all_themes = []
        for query in queries:
            all_themes.extend(detector.detect_themes(query))
        
        theme_values = [t["value"] for t in all_themes]
        assert theme_values.count("revenue") >= 4  # Revenue mentioned in all queries
        assert "metrics" in theme_values
        assert "trends" in theme_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
