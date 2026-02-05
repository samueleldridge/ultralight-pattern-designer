"""
Unit tests for Query Subscription System (Build #5)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, '/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/backend')

from app.intelligence.subscriptions import (
    SubscriptionService,
    SubscriptionFrequency,
    SubscriptionStatus,
    SubscriptionCondition,
    SubscriptionConditionType,
    QuerySubscription,
    SubscriptionResult,
    SubscriptionNotification
)


class TestSubscriptionFrequency:
    """Test SubscriptionFrequency enum"""
    
    def test_frequency_values(self):
        """Test frequency enum values"""
        assert SubscriptionFrequency.HOURLY.value == "hourly"
        assert SubscriptionFrequency.DAILY.value == "daily"
        assert SubscriptionFrequency.WEEKLY.value == "weekly"
        assert SubscriptionFrequency.MONTHLY.value == "monthly"


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.PAUSED.value == "paused"
        assert SubscriptionStatus.CANCELLED.value == "cancelled"


class TestSubscriptionConditionType:
    """Test SubscriptionConditionType enum"""
    
    def test_condition_type_values(self):
        """Test condition type enum values"""
        assert SubscriptionConditionType.THRESHOLD.value == "threshold"
        assert SubscriptionConditionType.CHANGE.value == "change"
        assert SubscriptionConditionType.NEW_ITEMS.value == "new_items"
        assert SubscriptionConditionType.ALWAYS.value == "always"


class TestSubscriptionService:
    """Test suite for SubscriptionService"""
    
    @pytest.fixture
    def subscription_service(self):
        return SubscriptionService(None, None, None)
    
    def test_generate_id(self, subscription_service):
        """Test ID generation"""
        id1 = subscription_service._generate_id()
        id2 = subscription_service._generate_id()
        
        assert id1 != id2
        assert len(id1) == 16
    
    def test_get_row_id_with_id(self, subscription_service):
        """Test getting row ID when id column exists"""
        row = {"id": 123, "name": "Test"}
        row_id = subscription_service._get_row_id(row)
        
        assert row_id == "123"
    
    def test_get_row_id_without_id(self, subscription_service):
        """Test getting row ID when no id column"""
        row = {"name": "Test", "value": 100}
        row_id = subscription_service._get_row_id(row)
        
        assert len(row_id) == 16  # Hash-based ID
    
    def test_calculate_next_run_hourly(self, subscription_service):
        """Test next run calculation for hourly"""
        next_run = subscription_service._calculate_next_run(SubscriptionFrequency.HOURLY)
        
        expected = datetime.utcnow() + timedelta(hours=1)
        assert (next_run - expected).total_seconds() < 1
    
    def test_calculate_next_run_daily(self, subscription_service):
        """Test next run calculation for daily"""
        next_run = subscription_service._calculate_next_run(SubscriptionFrequency.DAILY)
        
        expected = datetime.utcnow() + timedelta(days=1)
        assert (next_run - expected).total_seconds() < 1
    
    def test_calculate_next_run_weekly(self, subscription_service):
        """Test next run calculation for weekly"""
        next_run = subscription_service._calculate_next_run(SubscriptionFrequency.WEEKLY)
        
        expected = datetime.utcnow() + timedelta(weeks=1)
        assert (next_run - expected).total_seconds() < 1
    
    def test_calculate_next_run_monthly(self, subscription_service):
        """Test next run calculation for monthly"""
        next_run = subscription_service._calculate_next_run(SubscriptionFrequency.MONTHLY)
        
        expected = datetime.utcnow() + timedelta(days=30)
        assert (next_run - expected).total_seconds() < 1


class TestConditionEvaluation:
    """Test condition evaluation logic"""
    
    @pytest.fixture
    def subscription_service(self):
        return SubscriptionService(None, None, None)
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_always(self, subscription_service):
        """Test 'always' condition always returns true"""
        query_result = {"data": [{"value": 1}, {"value": 2}]}
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="always",
            condition_config={},
            query_result=query_result,
            last_result=None
        )
        
        assert met is True
        assert "Found 2 items" in details["summary"]
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_threshold_less_than(self, subscription_service):
        """Test threshold condition with less than operator"""
        query_result = {
            "data": [
                {"client": "A", "margin": 0.15},
                {"client": "B", "margin": 0.25},
                {"client": "C", "margin": 0.18}
            ]
        }
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="threshold",
            condition_config={"column": "margin", "operator": "<", "value": 0.20},
            query_result=query_result,
            last_result=None
        )
        
        assert met is True
        assert details["matching_count"] == 2  # A and C
        assert details["total_count"] == 3
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_threshold_greater_than(self, subscription_service):
        """Test threshold condition with greater than operator"""
        query_result = {
            "data": [
                {"client": "A", "revenue": 100},
                {"client": "B", "revenue": 200},
                {"client": "C", "revenue": 50}
            ]
        }
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="threshold",
            condition_config={"column": "revenue", "operator": ">", "value": 150},
            query_result=query_result,
            last_result=None
        )
        
        assert met is True
        assert details["matching_count"] == 1  # B only
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_threshold_no_match(self, subscription_service):
        """Test threshold condition with no matching rows"""
        query_result = {
            "data": [
                {"client": "A", "margin": 0.25},
                {"client": "B", "margin": 0.30}
            ]
        }
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="threshold",
            condition_config={"column": "margin", "operator": "<", "value": 0.20},
            query_result=query_result,
            last_result=None
        )
        
        assert met is False
        assert details["matching_count"] == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_new_items_first_run(self, subscription_service):
        """Test new_items condition on first run (no last_result)"""
        query_result = {
            "data": [
                {"id": 1, "name": "Client A"},
                {"id": 2, "name": "Client B"}
            ]
        }
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="new_items",
            condition_config={},
            query_result=query_result,
            last_result=None
        )
        
        assert met is True
        assert details["new_count"] == 2
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_new_items_found(self, subscription_service):
        """Test new_items condition finds new items"""
        query_result = {
            "data": [
                {"id": 1, "name": "Client A"},
                {"id": 2, "name": "Client B"},
                {"id": 3, "name": "Client C"}
            ]
        }
        last_result = [
            {"id": 1, "name": "Client A"},
            {"id": 2, "name": "Client B"}
        ]
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="new_items",
            condition_config={},
            query_result=query_result,
            last_result=last_result
        )
        
        assert met is True
        assert details["new_count"] == 1  # Client C is new
    
    @pytest.mark.asyncio
    async def test_evaluate_condition_new_items_none_found(self, subscription_service):
        """Test new_items condition with no new items"""
        query_result = {
            "data": [
                {"id": 1, "name": "Client A"},
                {"id": 2, "name": "Client B"}
            ]
        }
        last_result = [
            {"id": 1, "name": "Client A"},
            {"id": 2, "name": "Client B"}
        ]
        
        met, details = await subscription_service._evaluate_condition(
            condition_type="new_items",
            condition_config={},
            query_result=query_result,
            last_result=last_result
        )
        
        assert met is False
        assert details["new_count"] == 0


class TestSubscriptionCRUD:
    """Test subscription CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_subscription(self):
        """Test creating a subscription"""
        service = SubscriptionService(None, None, None)
        
        with patch('app.intelligence.subscriptions.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            subscription = await service.create_subscription(
                user_id="user1",
                tenant_id="tenant1",
                name="Low Margin Alert",
                query_template="SELECT * FROM clients WHERE gross_margin < 0.20",
                frequency=SubscriptionFrequency.WEEKLY,
                condition=SubscriptionCondition(
                    type=SubscriptionConditionType.THRESHOLD,
                    config={"column": "gross_margin", "operator": "<", "value": 0.20}
                ),
                description="Alert when clients have low margins"
            )
        
        assert subscription.name == "Low Margin Alert"
        assert subscription.user_id == "user1"
        assert subscription.tenant_id == "tenant1"
        assert subscription.frequency == "weekly"
        assert subscription.condition_type == "threshold"
        assert subscription.status == "active"
        assert subscription.next_run_at is not None


class TestFrequencyToCron:
    """Test frequency to cron expression mapping"""
    
    def test_hourly_cron(self):
        """Test hourly cron expression"""
        service = SubscriptionService(None, None, None)
        cron = service.FREQUENCY_TO_CRON[SubscriptionFrequency.HOURLY]
        assert cron == "0 * * * *"
    
    def test_daily_cron(self):
        """Test daily cron expression"""
        service = SubscriptionService(None, None, None)
        cron = service.FREQUENCY_TO_CRON[SubscriptionFrequency.DAILY]
        assert cron == "0 9 * * *"
    
    def test_weekly_cron(self):
        """Test weekly cron expression"""
        service = SubscriptionService(None, None, None)
        cron = service.FREQUENCY_TO_CRON[SubscriptionFrequency.WEEKLY]
        assert cron == "0 9 * * 1"
    
    def test_monthly_cron(self):
        """Test monthly cron expression"""
        service = SubscriptionService(None, None, None)
        cron = service.FREQUENCY_TO_CRON[SubscriptionFrequency.MONTHLY]
        assert cron == "0 9 1 * *"


class TestNotificationGeneration:
    """Test notification message generation"""
    
    @pytest.mark.asyncio
    async def test_send_notification_threshold_condition(self):
        """Test notification for threshold condition"""
        service = SubscriptionService(None, None, None)
        
        # Create mock subscription and result
        subscription = Mock()
        subscription.name = "Low Margin Alert"
        subscription.condition_type = "threshold"
        subscription.id = "sub123"
        subscription.user_id = "user1"
        subscription.tenant_id = "tenant1"
        subscription.description = "Alert when clients have low margins"
        
        result = Mock()
        result.condition_met = True
        result.condition_details = {"matching_count": 2}
        result.rows_found = 2
        
        # Mock the database
        with patch('app.intelligence.subscriptions.AsyncSessionLocal'):
            notification = await service._send_notification(subscription, result)
        
        assert notification is not None
        assert "Low Margin" in notification.title
        assert notification.action_prompt == "Would you like me to dive into this data for you?"


class TestIntegrationScenario:
    """End-to-end integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_weekly_margin_alert_workflow(self):
        """Test complete weekly margin alert workflow"""
        service = SubscriptionService(None, None, None)
        
        # 1. Create subscription
        with patch('app.intelligence.subscriptions.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            subscription = await service.create_subscription(
                user_id="user1",
                tenant_id="tenant1",
                name="Weekly Margin Check",
                query_template="SELECT * FROM clients WHERE gross_margin < 0.20",
                frequency=SubscriptionFrequency.WEEKLY,
                condition=SubscriptionCondition(
                    type=SubscriptionConditionType.THRESHOLD,
                    config={"column": "gross_margin", "operator": "<", "value": 0.20}
                )
            )
        
        assert subscription.status == "active"
        assert subscription.frequency == "weekly"
        
        # 2. Simulate execution with matching results
        query_result = {
            "sql": "SELECT * FROM clients WHERE gross_margin < 0.20",
            "data": [
                {"client_id": 1, "name": "Client A", "gross_margin": 0.15},
                {"client_id": 2, "name": "Client B", "gross_margin": 0.18}
            ],
            "row_count": 2
        }
        
        # 3. Evaluate condition
        met, details = await service._evaluate_condition(
            condition_type="threshold",
            condition_config={"column": "gross_margin", "operator": "<", "value": 0.20},
            query_result=query_result,
            last_result=None
        )
        
        assert met is True
        assert details["matching_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
