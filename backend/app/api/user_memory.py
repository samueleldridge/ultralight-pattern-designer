"""
User Memory & Proactive Intelligence API

Endpoints:
- GET /api/users/me/memory - Get user's long-term memory
- GET /api/users/me/interactions - Get interaction history
- GET /api/users/me/suggestions - Get proactive suggestions
- POST /api/users/me/suggestions/:id/dismiss - Dismiss a suggestion
- POST /api/users/me/suggestions/:id/click - Mark suggestion as clicked
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.intelligence.user_memory import (
    UserMemoryService,
    ProactiveIntelligenceService,
    ProactiveSuggestion
)
from app.middleware import get_current_user

router = APIRouter(prefix="/api/users", tags=["user_memory"])


# Response Models
class UserInterestResponse(BaseModel):
    topic: str
    category: str
    frequency: int
    confidence: float


class UserMemoryResponse(BaseModel):
    user_id: str
    interests: List[UserInterestResponse]
    preferred_chart_types: List[str]
    memory_summary: str
    updated_at: datetime


class UserInteractionResponse(BaseModel):
    id: str
    query: str
    themes: List[str]
    entities_mentioned: List[str]
    chart_type: Optional[str]
    created_at: datetime


class ProactiveSuggestionResponse(BaseModel):
    id: str
    title: str
    description: str
    suggested_query: str
    reason: str
    priority: str
    created_at: datetime


# Services (singleton pattern)
_memory_service: Optional[UserMemoryService] = None
_proactive_service: Optional[ProactiveIntelligenceService] = None


def get_memory_service() -> UserMemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = UserMemoryService()
    return _memory_service


def get_proactive_service() -> ProactiveIntelligenceService:
    global _proactive_service
    if _proactive_service is None:
        # Would need to inject real db_connector and llm_factory
        _proactive_service = ProactiveIntelligenceService(None, None)
    return _proactive_service


@router.get("/me/memory", response_model=UserMemoryResponse)
async def get_user_memory(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current user's long-term memory profile.
    
    Returns consolidated interests, preferences, and usage patterns
    based on historical query analysis.
    """
    service = get_memory_service()
    
    profile = await service.get_or_create_profile(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    return UserMemoryResponse(
        user_id=profile.user_id,
        interests=[
            UserInterestResponse(**interest)
            for interest in profile.interests
        ],
        preferred_chart_types=profile.preferred_chart_types,
        memory_summary=profile.memory_summary,
        updated_at=profile.updated_at
    )


@router.post("/me/memory/consolidate")
async def consolidate_user_memory(
    lookback_days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger manual memory consolidation.
    
    Analyzes recent interactions and updates the user's
    long-term memory profile.
    """
    service = get_memory_service()
    
    profile = await service.consolidate_memory(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        lookback_days=lookback_days
    )
    
    return {
        "status": "success",
        "interests_found": len(profile.interests),
        "memory_summary": profile.memory_summary,
        "updated_at": profile.updated_at.isoformat()
    }


@router.get("/me/interactions", response_model=List[UserInteractionResponse])
async def get_user_interactions(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's interaction history with the LLM.
    
    Returns queries, extracted themes, and metadata about
    each conversation.
    """
    from app.intelligence.user_memory import UserInteraction
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, desc
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserInteraction).where(
                UserInteraction.user_id == current_user["id"],
                UserInteraction.tenant_id == current_user["tenant_id"]
            ).order_by(
                desc(UserInteraction.created_at)
            ).offset(offset).limit(limit)
        )
        
        interactions = result.scalars().all()
        
        return [
            UserInteractionResponse(
                id=i.id,
                query=i.query,
                themes=i.themes,
                entities_mentioned=i.entities_mentioned,
                chart_type=i.chart_type,
                created_at=i.created_at
            )
            for i in interactions
        ]


@router.get("/me/suggestions", response_model=List[ProactiveSuggestionResponse])
async def get_proactive_suggestions(
    limit: int = 10,
    include_delivered: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get proactive suggestions for the user.
    
    Returns AI-generated suggestions based on:
    - User's historical interests
    - New data discoveries
    - Anomaly detection
    - Trend analysis
    """
    service = get_proactive_service()
    
    suggestions = await service.get_pending_suggestions(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    
    return [
        ProactiveSuggestionResponse(
            id=s.id,
            title=s.title,
            description=s.description,
            suggested_query=s.suggested_query,
            reason=s.reason,
            priority=s.priority.value,
            created_at=s.created_at
        )
        for s in suggestions
    ]


@router.post("/me/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Dismiss a proactive suggestion"""
    from app.intelligence.user_memory import ProactiveSuggestionRecord
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProactiveSuggestionRecord).where(
                ProactiveSuggestionRecord.id == suggestion_id,
                ProactiveSuggestionRecord.user_id == current_user["id"]
            )
        )
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        record.dismissed = True
        await session.commit()
        
        return {"status": "dismissed"}


@router.post("/me/suggestions/{suggestion_id}/click")
async def click_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a suggestion as clicked/viewed"""
    from app.intelligence.user_memory import ProactiveSuggestionRecord
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProactiveSuggestionRecord).where(
                ProactiveSuggestionRecord.id == suggestion_id,
                ProactiveSuggestionRecord.user_id == current_user["id"]
            )
        )
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        record.clicked = True
        record.viewed = True
        await session.commit()
        
        return {"status": "clicked", "suggested_query": record.suggestion_data.get("suggested_query")}


@router.get("/me/analytics")
async def get_user_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get analytics about user's querying behavior.
    
    Returns insights like:
    - Query frequency over time
    - Most active hours
    - Topic distribution
    - Query complexity trends
    """
    from app.intelligence.user_memory import UserInteraction
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func, and_
    from datetime import datetime, timedelta
    
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Total queries
        total_result = await session.execute(
            select(func.count(UserInteraction.id)).where(
                UserInteraction.user_id == current_user["id"],
                UserInteraction.tenant_id == current_user["tenant_id"],
                UserInteraction.created_at >= cutoff
            )
        )
        total_queries = total_result.scalar()
        
        # Top themes
        themes_result = await session.execute(
            select(
                func.unnest(UserInteraction.themes).label("theme"),
                func.count().label("count")
            ).where(
                UserInteraction.user_id == current_user["id"],
                UserInteraction.tenant_id == current_user["tenant_id"],
                UserInteraction.created_at >= cutoff
            ).group_by("theme").order_by(desc("count")).limit(10)
        )
        top_themes = [{"theme": row[0], "count": row[1]} for row in themes_result.fetchall()]
        
        # Queries by day
        daily_result = await session.execute(
            select(
                func.date(UserInteraction.created_at).label("date"),
                func.count().label("count")
            ).where(
                UserInteraction.user_id == current_user["id"],
                UserInteraction.tenant_id == current_user["tenant_id"],
                UserInteraction.created_at >= cutoff
            ).group_by("date").order_by("date")
        )
        daily_queries = [{"date": row[0], "count": row[1]} for row in daily_result.fetchall()]
        
        return {
            "period_days": days,
            "total_queries": total_queries,
            "avg_queries_per_day": round(total_queries / days, 1) if days > 0 else 0,
            "top_themes": top_themes,
            "daily_activity": daily_queries
        }
