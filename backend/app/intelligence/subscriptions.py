"""
Query Subscription System

Users can subscribe to queries with conditions:
- "Tell me if gross margin falls below 20%"
- "Weekly report on new customers"
- "Alert if revenue drops more than 10%"

Features:
- Create subscription with schedule and condition
- Dynamic cron job per subscription
- Condition evaluation against live data
- Notifications when conditions are met
- Cancel/pause subscriptions
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
import json
import hashlib

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON
from sqlalchemy import select, desc, and_, or_
from app.database import Base, AsyncSessionLocal


class SubscriptionFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class SubscriptionConditionType(str, Enum):
    THRESHOLD = "threshold"  # value >/< threshold
    CHANGE = "change"        # % change over time
    NEW_ITEMS = "new_items"  # New records since last check
    ALWAYS = "always"        # Always report (for weekly summaries)


class QuerySubscription(Base):
    """User subscription to a monitored query"""
    __tablename__ = "query_subscriptions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    
    # Subscription details
    name = Column(String, nullable=False)  # "Low Margin Alert"
    description = Column(Text)  # User-friendly description
    
    # The query to monitor
    query_template = Column(Text, nullable=False)  # SQL or natural language
    query_type = Column(String, default="sql")  # sql, nl
    
    # Schedule
    frequency = Column(String, nullable=False)  # hourly, daily, weekly, monthly
    cron_expression = Column(String)  # Custom cron if needed
    next_run_at = Column(DateTime)
    last_run_at = Column(DateTime)
    
    # Condition to check
    condition_type = Column(String, nullable=False)  # threshold, change, new_items, always
    condition_config = Column(JSON, default=dict)
    # Examples:
    # threshold: {"column": "gross_margin", "operator": "<", "value": 0.20}
    # change: {"column": "revenue", "change_percent": -10, "period": "day"}
    # new_items: {"table": "clients", "since_last_check": true}
    
    # Status
    status = Column(String, default="active")  # active, paused, cancelled
    
    # Notification settings
    notify_on_condition_only = Column(Boolean, default=True)  # Only notify if condition met
    notification_channel = Column(String, default="in_app")  # in_app, email, slack
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    run_count = Column(Integer, default=0)
    hit_count = Column(Integer, default=0)  # Times condition was met
    
    # Last result snapshot
    last_result = Column(JSON)
    last_result_summary = Column(Text)


class SubscriptionResult(Base):
    """Record of each subscription check"""
    __tablename__ = "subscription_results"
    
    id = Column(String, primary_key=True)
    subscription_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    
    # Execution details
    executed_at = Column(DateTime, default=datetime.utcnow)
    query_executed = Column(Text)  # Actual SQL run
    
    # Results
    rows_found = Column(Integer)
    result_data = Column(JSON)  # Limited snapshot
    
    # Condition evaluation
    condition_met = Column(Boolean, default=False)
    condition_details = Column(JSON)  # Why condition was/wasn't met
    
    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_delivered_at = Column(DateTime)
    notification_message = Column(Text)
    
    # User interaction
    viewed_by_user = Column(Boolean, default=False)
    user_action = Column(String)  # dismissed, explored, converted_to_dashboard


@dataclass
class SubscriptionCondition:
    """Condition configuration for a subscription"""
    type: SubscriptionConditionType
    config: Dict[str, Any]
    
    def to_dict(self):
        return {
            "type": self.type.value,
            "config": self.config
        }


@dataclass
class SubscriptionNotification:
    """Notification generated for a subscription"""
    id: str
    subscription_id: str
    user_id: str
    tenant_id: str
    title: str
    message: str
    context: str  # Additional context
    result_summary: str
    action_prompt: str  # "Would you like me to dive into this data?"
    created_at: datetime
    read: bool = False


class SubscriptionService:
    """Service for managing query subscriptions"""
    
    FREQUENCY_TO_CRON = {
        SubscriptionFrequency.HOURLY: "0 * * * *",  # Every hour
        SubscriptionFrequency.DAILY: "0 9 * * *",     # Daily at 9am
        SubscriptionFrequency.WEEKLY: "0 9 * * 1",    # Mondays at 9am
        SubscriptionFrequency.MONTHLY: "0 9 1 * *",   # 1st of month at 9am
    }
    
    def __init__(self, db_executor, llm_service, cron_service):
        self.db = db_executor
        self.llm = llm_service
        self.cron = cron_service
    
    async def create_subscription(
        self,
        user_id: str,
        tenant_id: str,
        name: str,
        query_template: str,
        frequency: SubscriptionFrequency,
        condition: SubscriptionCondition,
        description: Optional[str] = None,
        notify_on_condition_only: bool = True
    ) -> QuerySubscription:
        """Create a new query subscription"""
        
        subscription_id = self._generate_id()
        
        # Calculate next run time
        next_run = self._calculate_next_run(frequency)
        
        async with AsyncSessionLocal() as session:
            subscription = QuerySubscription(
                id=subscription_id,
                user_id=user_id,
                tenant_id=tenant_id,
                name=name,
                description=description,
                query_template=query_template,
                frequency=frequency.value,
                cron_expression=self.FREQUENCY_TO_CRON.get(frequency),
                next_run_at=next_run,
                condition_type=condition.type.value,
                condition_config=condition.config,
                notify_on_condition_only=notify_on_condition_only,
                status=SubscriptionStatus.ACTIVE.value
            )
            
            session.add(subscription)
            await session.commit()
            
            # Register cron job for this subscription
            await self._register_cron_job(subscription)
            
            return subscription
    
    async def execute_subscription_check(
        self,
        subscription_id: str
    ) -> Optional[SubscriptionResult]:
        """Execute a subscription check and evaluate condition"""
        
        async with AsyncSessionLocal() as session:
            # Get subscription
            result = await session.execute(
                select(QuerySubscription).where(
                    QuerySubscription.id == subscription_id
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription or subscription.status != SubscriptionStatus.ACTIVE.value:
                return None
            
            # Execute the query
            query_result = await self._execute_query(
                subscription.query_template,
                subscription.tenant_id
            )
            
            # Evaluate condition
            condition_met, condition_details = await self._evaluate_condition(
                subscription.condition_type,
                subscription.condition_config,
                query_result,
                subscription.last_result
            )
            
            # Create result record
            result_record = SubscriptionResult(
                id=self._generate_id(),
                subscription_id=subscription_id,
                user_id=subscription.user_id,
                tenant_id=subscription.tenant_id,
                query_executed=query_result.get("sql", ""),
                rows_found=query_result.get("row_count", 0),
                result_data=query_result.get("data", [])[:10],  # Limit stored data
                condition_met=condition_met,
                condition_details=condition_details
            )
            
            session.add(result_record)
            
            # Update subscription
            subscription.last_run_at = datetime.utcnow()
            subscription.next_run_at = self._calculate_next_run(
                SubscriptionFrequency(subscription.frequency)
            )
            subscription.run_count += 1
            subscription.last_result = query_result.get("data", [])
            
            if condition_met:
                subscription.hit_count += 1
                subscription.last_result_summary = condition_details.get("summary", "")
            
            await session.commit()
            
            # Send notification if condition met (or if always notify)
            if condition_met or not subscription.notify_on_condition_only:
                await self._send_notification(subscription, result_record)
            
            return result_record
    
    async def _execute_query(
        self,
        query_template: str,
        tenant_id: str
    ) -> Dict:
        """Execute the subscription query"""
        # This would integrate with your existing query execution pipeline
        # For now, return mock structure
        return {
            "sql": query_template,
            "data": [],
            "row_count": 0,
            "columns": []
        }
    
    async def _evaluate_condition(
        self,
        condition_type: str,
        condition_config: Dict,
        query_result: Dict,
        last_result: Optional[List]
    ) -> tuple[bool, Dict]:
        """Evaluate if condition is met"""
        
        data = query_result.get("data", [])
        
        if condition_type == SubscriptionConditionType.ALWAYS.value:
            return True, {"summary": f"Found {len(data)} items"}
        
        elif condition_type == SubscriptionConditionType.THRESHOLD.value:
            column = condition_config.get("column")
            operator = condition_config.get("operator")
            threshold = condition_config.get("value")
            
            matching = []
            for row in data:
                value = row.get(column)
                if value is None:
                    continue
                    
                if operator == "<" and value < threshold:
                    matching.append(row)
                elif operator == ">" and value > threshold:
                    matching.append(row)
                elif operator == "=" and value == threshold:
                    matching.append(row)
                elif operator == "<=" and value <= threshold:
                    matching.append(row)
                elif operator == ">=" and value >= threshold:
                    matching.append(row)
            
            return len(matching) > 0, {
                "matching_count": len(matching),
                "total_count": len(data),
                "threshold": threshold,
                "summary": f"Found {len(matching)} items below threshold"
            }
        
        elif condition_type == SubscriptionConditionType.NEW_ITEMS.value:
            # Compare with last result to find new items
            if not last_result:
                return len(data) > 0, {
                    "new_count": len(data),
                    "summary": f"Found {len(data)} items (first check)"
                }
            
            # Simple ID-based comparison
            last_ids = {self._get_row_id(r) for r in last_result}
            new_items = [r for r in data if self._get_row_id(r) not in last_ids]
            
            return len(new_items) > 0, {
                "new_count": len(new_items),
                "total_count": len(data),
                "summary": f"Found {len(new_items)} new items"
            }
        
        elif condition_type == SubscriptionConditionType.CHANGE.value:
            # Would need historical data comparison
            # Simplified for MVP
            return False, {"summary": "Change detection requires historical data"}
        
        return False, {"summary": "Unknown condition type"}
    
    async def _send_notification(
        self,
        subscription: QuerySubscription,
        result: SubscriptionResult
    ):
        """Generate and send notification"""
        
        # Generate human-readable message
        if result.condition_met:
            if subscription.condition_type == SubscriptionConditionType.THRESHOLD.value:
                message = (
                    f"I found {result.condition_details.get('matching_count', 0)} "
                    f"{subscription.name.lower()}. "
                )
            elif subscription.condition_type == SubscriptionConditionType.NEW_ITEMS.value:
                message = (
                    f"I found {result.condition_details.get('new_count', 0)} new "
                    f"{subscription.name.lower()}. "
                )
            else:
                message = f"Your {subscription.name} check found results."
        else:
            message = f"Your {subscription.name} check completed. No issues found."
        
        notification = SubscriptionNotification(
            id=self._generate_id(),
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            tenant_id=subscription.tenant_id,
            title=subscription.name,
            message=message,
            context=subscription.description or "",
            result_summary=result.condition_details.get("summary", ""),
            action_prompt="Would you like me to dive into this data for you?",
            created_at=datetime.utcnow()
        )
        
        # Store notification
        result.notification_message = message
        result.notification_sent = True
        result.notification_delivered_at = datetime.utcnow()
        
        # Here you would also send via channel (email, slack, etc.)
        # For now, it's stored for in-app retrieval
        
        async with AsyncSessionLocal() as session:
            await session.commit()
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """Cancel a subscription"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(QuerySubscription).where(
                    and_(
                        QuerySubscription.id == subscription_id,
                        QuerySubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False
            
            subscription.status = SubscriptionStatus.CANCELLED.value
            await session.commit()
            
            # Unregister cron job
            await self._unregister_cron_job(subscription_id)
            
            return True
    
    async def pause_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """Pause a subscription"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(QuerySubscription).where(
                    and_(
                        QuerySubscription.id == subscription_id,
                        QuerySubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False
            
            subscription.status = SubscriptionStatus.PAUSED.value
            await session.commit()
            
            # Unregister cron job
            await self._unregister_cron_job(subscription_id)
            
            return True
    
    async def resume_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """Resume a paused subscription"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(QuerySubscription).where(
                    and_(
                        QuerySubscription.id == subscription_id,
                        QuerySubscription.user_id == user_id
                    )
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False
            
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.next_run_at = self._calculate_next_run(
                SubscriptionFrequency(subscription.frequency)
            )
            await session.commit()
            
            # Re-register cron job
            await self._register_cron_job(subscription)
            
            return True
    
    async def get_user_subscriptions(
        self,
        user_id: str,
        tenant_id: str,
        status: Optional[str] = None
    ) -> List[QuerySubscription]:
        """Get all subscriptions for a user"""
        
        async with AsyncSessionLocal() as session:
            query = select(QuerySubscription).where(
                and_(
                    QuerySubscription.user_id == user_id,
                    QuerySubscription.tenant_id == tenant_id
                )
            )
            
            if status:
                query = query.where(QuerySubscription.status == status)
            
            query = query.order_by(desc(QuerySubscription.created_at))
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_pending_notifications(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """Get pending notifications for user"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SubscriptionResult, QuerySubscription).join(
                    QuerySubscription,
                    SubscriptionResult.subscription_id == QuerySubscription.id
                ).where(
                    and_(
                        SubscriptionResult.user_id == user_id,
                        SubscriptionResult.tenant_id == tenant_id,
                        SubscriptionResult.notification_sent == True,
                        SubscriptionResult.viewed_by_user == False
                    )
                ).order_by(
                    desc(SubscriptionResult.executed_at)
                ).limit(limit)
            )
            
            notifications = []
            for result, subscription in result.fetchall():
                notifications.append({
                    "id": result.id,
                    "subscription_id": subscription.id,
                    "subscription_name": subscription.name,
                    "message": result.notification_message,
                    "condition_met": result.condition_met,
                    "rows_found": result.rows_found,
                    "executed_at": result.executed_at.isoformat(),
                    "action_prompt": "Would you like me to dive into this data for you?"
                })
            
            return notifications
    
    def _calculate_next_run(self, frequency: SubscriptionFrequency) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.utcnow()
        
        if frequency == SubscriptionFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif frequency == SubscriptionFrequency.DAILY:
            return now + timedelta(days=1)
        elif frequency == SubscriptionFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == SubscriptionFrequency.MONTHLY:
            # Approximate
            return now + timedelta(days=30)
        
        return now + timedelta(days=1)
    
    def _get_row_id(self, row: Dict) -> str:
        """Generate ID for a row for comparison"""
        # Use first column or generate hash
        if "id" in row:
            return str(row["id"])
        return hashlib.sha256(str(row).encode()).hexdigest()[:16]
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
    
    async def _register_cron_job(self, subscription: QuerySubscription):
        """Register a cron job for this subscription"""
        # This would integrate with your cron system
        # For now, it's a placeholder
        pass
    
    async def _unregister_cron_job(self, subscription_id: str):
        """Unregister a subscription's cron job"""
        # Placeholder
        pass
