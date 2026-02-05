"""
Query Subscriptions API

Endpoints:
- POST /api/subscriptions - Create new subscription
- GET /api/subscriptions - List user subscriptions
- GET /api/subscriptions/:id - Get subscription details
- POST /api/subscriptions/:id/pause - Pause subscription
- POST /api/subscriptions/:id/resume - Resume subscription
- DELETE /api/subscriptions/:id - Cancel subscription
- GET /api/subscriptions/notifications - Get pending notifications
- POST /api/subscriptions/notifications/:id/view - Mark as viewed
- POST /api/subscriptions/:id/run-now - Execute immediately
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from app.intelligence.subscriptions import (
    SubscriptionService,
    SubscriptionFrequency,
    SubscriptionCondition,
    SubscriptionConditionType
)
from app.middleware import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


# Request/Response Models
class CreateSubscriptionRequest(BaseModel):
    name: str = Field(..., description="Name of the subscription")
    description: Optional[str] = Field(None, description="Description of what this monitors")
    query_template: str = Field(..., description="SQL query or natural language query to monitor")
    query_type: str = Field("sql", description="Type: sql or nl")
    frequency: str = Field(..., description="hourly, daily, weekly, or monthly")
    condition_type: str = Field(..., description="threshold, change, new_items, or always")
    condition_config: dict = Field(..., description="Condition configuration")
    notify_on_condition_only: bool = Field(True, description="Only notify when condition is met")
    notification_channel: str = Field("in_app", description="in_app, email, or slack")


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    query_template: str
    frequency: str
    condition_type: str
    status: str
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    run_count: int
    hit_count: int
    created_at: datetime


class SubscriptionNotificationResponse(BaseModel):
    id: str
    subscription_id: str
    subscription_name: str
    message: str
    condition_met: bool
    rows_found: int
    executed_at: str
    action_prompt: str


class RunNowResponse(BaseModel):
    executed: bool
    condition_met: bool
    rows_found: int
    summary: str


# Service singleton
_subscription_service: Optional[SubscriptionService] = None


def get_subscription_service() -> SubscriptionService:
    global _subscription_service
    if _subscription_service is None:
        # Would inject real dependencies
        _subscription_service = SubscriptionService(None, None, None)
    return _subscription_service


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new query subscription.
    
    Example:
    ```json
    {
      "name": "Low Margin Alert",
      "description": "Alert when clients have gross margin below 20%",
      "query_template": "SELECT * FROM clients WHERE gross_margin < 0.20",
      "frequency": "weekly",
      "condition_type": "threshold",
      "condition_config": {"column": "gross_margin", "operator": "<", "value": 0.20}
    }
    ```
    """
    service = get_subscription_service()
    
    try:
        frequency = SubscriptionFrequency(request.frequency)
        condition = SubscriptionCondition(
            type=SubscriptionConditionType(request.condition_type),
            config=request.condition_config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid frequency or condition type: {e}")
    
    subscription = await service.create_subscription(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        name=request.name,
        query_template=request.query_template,
        frequency=frequency,
        condition=condition,
        description=request.description,
        notify_on_condition_only=request.notify_on_condition_only
    )
    
    return SubscriptionResponse(
        id=subscription.id,
        name=subscription.name,
        description=subscription.description,
        query_template=subscription.query_template,
        frequency=subscription.frequency,
        condition_type=subscription.condition_type,
        status=subscription.status,
        next_run_at=subscription.next_run_at,
        last_run_at=subscription.last_run_at,
        run_count=subscription.run_count,
        hit_count=subscription.hit_count,
        created_at=subscription.created_at
    )


@router.get("", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all subscriptions for the current user"""
    service = get_subscription_service()
    
    subscriptions = await service.get_user_subscriptions(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        status=status
    )
    
    return [
        SubscriptionResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            query_template=s.query_template,
            frequency=s.frequency,
            condition_type=s.condition_type,
            status=s.status,
            next_run_at=s.next_run_at,
            last_run_at=s.last_run_at,
            run_count=s.run_count,
            hit_count=s.hit_count,
            created_at=s.created_at
        )
        for s in subscriptions
    ]


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get details of a specific subscription"""
    service = get_subscription_service()
    
    subscriptions = await service.get_user_subscriptions(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    subscription = next((s for s in subscriptions if s.id == subscription_id), None)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return SubscriptionResponse(
        id=subscription.id,
        name=subscription.name,
        description=subscription.description,
        query_template=subscription.query_template,
        frequency=subscription.frequency,
        condition_type=subscription.condition_type,
        status=subscription.status,
        next_run_at=subscription.next_run_at,
        last_run_at=subscription.last_run_at,
        run_count=subscription.run_count,
        hit_count=subscription.hit_count,
        created_at=subscription.created_at
    )


@router.post("/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pause a subscription (stops scheduled checks)"""
    service = get_subscription_service()
    
    success = await service.pause_subscription(
        subscription_id=subscription_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"status": "paused", "subscription_id": subscription_id}


@router.post("/{subscription_id}/resume")
async def resume_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Resume a paused subscription"""
    service = get_subscription_service()
    
    success = await service.resume_subscription(
        subscription_id=subscription_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"status": "active", "subscription_id": subscription_id}


@router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel (permanently delete) a subscription"""
    service = get_subscription_service()
    
    success = await service.cancel_subscription(
        subscription_id=subscription_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"status": "cancelled", "subscription_id": subscription_id}


@router.post("/{subscription_id}/run-now", response_model=RunNowResponse)
async def run_subscription_now(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Execute a subscription check immediately (for testing)"""
    service = get_subscription_service()
    
    # Verify ownership
    subscriptions = await service.get_user_subscriptions(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    if not any(s.id == subscription_id for s in subscriptions):
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    result = await service.execute_subscription_check(subscription_id)
    
    if not result:
        raise HTTPException(status_code=400, detail="Failed to execute subscription")
    
    return RunNowResponse(
        executed=True,
        condition_met=result.condition_met,
        rows_found=result.rows_found,
        summary=result.condition_details.get("summary", "Check completed")
    )


@router.get("/notifications/pending", response_model=List[SubscriptionNotificationResponse])
async def get_pending_notifications(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Get pending notifications from subscriptions.
    
    Returns notifications like:
    "Hi Sam, I checked if there were any new clients with gross margin 
    less than 20% as you requested and found 2 new clients. Would you 
    like me to dive into this data for you?"
    """
    service = get_subscription_service()
    
    notifications = await service.get_pending_notifications(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    
    return [SubscriptionNotificationResponse(**n) for n in notifications]


@router.post("/notifications/{notification_id}/view")
async def mark_notification_viewed(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as viewed by the user"""
    from app.intelligence.subscriptions import SubscriptionResult
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SubscriptionResult).where(
                and_(
                    SubscriptionResult.id == notification_id,
                    SubscriptionResult.user_id == current_user["id"]
                )
            )
        )
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        record.viewed_by_user = True
        await session.commit()
        
        return {"status": "viewed", "notification_id": notification_id}


@router.post("/notifications/{notification_id}/explore")
async def explore_notification_data(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    User wants to explore the data from a notification.
    Returns the full query results for analysis.
    """
    from app.intelligence.subscriptions import SubscriptionResult, QuerySubscription
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    
    async with AsyncSessionLocal() as session:
        # Get the result and subscription
        result = await session.execute(
            select(SubscriptionResult, QuerySubscription).join(
                QuerySubscription,
                SubscriptionResult.subscription_id == QuerySubscription.id
            ).where(
                and_(
                    SubscriptionResult.id == notification_id,
                    SubscriptionResult.user_id == current_user["id"]
                )
            )
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        result_record, subscription = row
        
        # Mark as explored
        result_record.user_action = "explored"
        result_record.viewed_by_user = True
        await session.commit()
        
        return {
            "notification_id": notification_id,
            "subscription_name": subscription.name,
            "query_executed": result_record.query_executed,
            "data": result_record.result_data,
            "rows_found": result_record.rows_found,
            "suggested_next_query": f"Tell me more about these {subscription.name.lower()}"
        }
