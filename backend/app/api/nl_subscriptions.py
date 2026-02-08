"""
Natural Language Subscriptions API

Allows users to subscribe/unsubscribe via natural language in chat.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.intelligence.nl_subscriptions import NLSubscriptionManager
from app.intelligence.subscriptions import get_subscription_service
from app.middleware import get_current_user

router = APIRouter(prefix="/api/nl-subscriptions", tags=["nl_subscriptions"])


# Request/Response Models
class NLSubscriptionRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class NLSubscriptionResponse(BaseModel):
    success: bool
    action: str  # subscribe, unsubscribe, list, unknown
    message: str
    subscription_id: Optional[str] = None
    details: Optional[dict] = None
    suggestions: Optional[list] = None


# Singleton
_nl_manager = None


def get_nl_manager():
    global _nl_manager
    if _nl_manager is None:
        sub_service = get_subscription_service()
        _nl_manager = NLSubscriptionManager(sub_service)
    return _nl_manager


@router.post("/process", response_model=NLSubscriptionResponse)
async def process_nl_subscription(
    request: NLSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process a natural language subscription message.
    
    Examples:
    - "Tell me the highest revenue client weekly"
    - "Alert me when revenue drops below 10k"
    - "Stop that weekly alert"
    - "What am I subscribed to?"
    """
    manager = get_nl_manager()
    
    result = await manager.handle_message(
        text=request.message,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        session_id=request.session_id
    )
    
    return NLSubscriptionResponse(
        success=result.get('success', False),
        action=result.get('action', 'unknown'),
        message=result.get('message', ''),
        subscription_id=result.get('subscription_id'),
        details=result.get('details'),
        suggestions=result.get('suggestions') or result.get('subscription', [])
    )


@router.get("/examples")
async def get_examples():
    """Get example natural language subscription commands"""
    return {
        "subscribe_examples": [
            {
                "phrase": "Tell me my top revenue clients weekly",
                "description": "Weekly report of highest revenue clients"
            },
            {
                "phrase": "Alert me when gross margin drops below 20%",
                "description": "Threshold alert for low margin"
            },
            {
                "phrase": "Notify me of new customers daily",
                "description": "Daily notification for new signups"
            },
            {
                "phrase": "Track revenue changes over 10%",
                "description": "Alert on significant revenue swings"
            },
            {
                "phrase": "Send me a summary every month",
                "description": "Monthly summary report"
            }
        ],
        "unsubscribe_examples": [
            {
                "phrase": "Unsubscribe from the revenue alert",
                "description": "Cancel by name"
            },
            {
                "phrase": "Stop that weekly notification",
                "description": "Cancel most recent"
            },
            {
                "phrase": "Turn off the margin alerts",
                "description": "Cancel by keyword"
            },
            {
                "phrase": "Cancel all my subscriptions",
                "description": "Cancel everything (with confirmation)"
            }
        ],
        "list_examples": [
            {
                "phrase": "What am I subscribed to?",
                "description": "List all subscriptions"
            },
            {
                "phrase": "Show my alerts",
                "description": "Quick list"
            }
        ]
    }
