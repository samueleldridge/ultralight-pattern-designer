from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.intelligence.proactive import (
    ProactiveInsightGenerator,
    PatternDetector,
    SuggestionEngine,
    UserProfileUpdater
)
from app.schemas import SuggestionResponse, InsightResponse

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/suggestions", response_model=List[SuggestionResponse])
async def get_suggestions(
    user_id: str = "demo-user",
    tenant_id: str = "demo-tenant",
    db: AsyncSession = Depends(get_db)
):
    """Get personalized suggestions for user"""
    
    generator = ProactiveInsightGenerator()
    
    # Generate fresh insights
    insights = await generator.generate_insights_for_user(user_id, tenant_id)
    
    # Get pending insights
    pending = await generator.get_pending_insights(user_id, limit=5)
    
    return [
        SuggestionResponse(
            type=i["type"],
            text=i["title"],
            subtitle=i.get("description"),
            query=i.get("suggested_query"),
            confidence=i.get("confidence", 0.5)
        )
        for i in insights + pending
    ]


@router.get("/insights/pending")
async def get_pending_insights(
    user_id: str = "demo-user",
    limit: int = 10
):
    """Get pending proactive insights"""
    
    generator = ProactiveInsightGenerator()
    insights = await generator.get_pending_insights(user_id, limit)
    
    return [
        InsightResponse(
            id=i["id"],
            type=i["type"],
            title=i["title"],
            description=i.get("description"),
            suggested_query=i.get("suggested_query"),
            created_at=i["created_at"]
        )
        for i in insights
    ]


@router.post("/insights/{insight_id}/feedback")
async def submit_insight_feedback(
    insight_id: str,
    feedback: str,  # 'helpful', 'not_helpful', 'irrelevant'
):
    """Submit feedback on an insight"""
    
    generator = ProactiveInsightGenerator()
    await generator.record_feedback(insight_id, feedback)
    
    return {"status": "recorded"}


@router.post("/insights/{insight_id}/dismiss")
async def dismiss_insight(insight_id: str):
    """Dismiss an insight"""
    
    generator = ProactiveInsightGenerator()
    await generator.mark_insight_delivered(insight_id)
    
    return {"status": "dismissed"}


@router.get("/patterns")
async def get_user_patterns(
    user_id: str = "demo-user",
    tenant_id: str = "demo-tenant"
):
    """Get detected patterns for user"""
    
    detector = PatternDetector()
    patterns = await detector.analyze_user_patterns(user_id, tenant_id)
    
    return [
        {
            "type": p.pattern_type,
            "description": p.description,
            "confidence": p.confidence,
            "data": p.data,
            "detected_at": p.detected_at.isoformat()
        }
        for p in patterns
    ]


@router.post("/profile/update")
async def update_user_profile(
    user_id: str = "demo-user",
    tenant_id: str = "demo-tenant"
):
    """Manually trigger profile update"""
    
    updater = UserProfileUpdater()
    await updater.update_profile(user_id, tenant_id)
    
    return {"status": "updated"}


@router.post("/generate-insights")
async def trigger_insight_generation(
    user_id: str = "demo-user",
    tenant_id: str = "demo-tenant"
):
    """Manually trigger insight generation"""
    
    generator = ProactiveInsightGenerator()
    insights = await generator.generate_insights_for_user(user_id, tenant_id)
    
    # Deliver insights
    delivered = []
    for insight in insights:
        insight_id = await generator.deliver_insight(user_id, tenant_id, insight)
        delivered.append({"id": insight_id, **insight})
    
    return {
        "generated": len(insights),
        "insights": delivered
    }
