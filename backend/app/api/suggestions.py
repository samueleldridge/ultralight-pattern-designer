"""
Suggestions API - Provides AI-powered suggestions and search functionality
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


class SuggestionResponse(BaseModel):
    """Suggestion response schema matching frontend expectations"""
    type: str  # 'pattern', 'popular', 'trending', 'recent'
    text: str  # Main display text
    subtitle: Optional[str] = None  # Secondary text
    action: Optional[str] = None  # 'run', 'suggest', 'open'
    query: Optional[str] = None  # The actual query to run
    confidence: Optional[float] = 0.5  # Confidence score 0-1
    icon: Optional[str] = None  # Icon identifier
    category: Optional[str] = None  # Category for grouping


class HistoryItem(BaseModel):
    """History search result item"""
    id: str
    query: str
    timestamp: datetime
    result_count: Optional[int] = None
    is_favorite: bool = False


class SuggestionsListResponse(BaseModel):
    """Wrapper for suggestions list"""
    suggestions: List[SuggestionResponse]
    total: int
    generated_at: datetime


# Mock suggestions database - in production this would be AI-generated
MOCK_SUGGESTIONS = [
    {
        "type": "pattern",
        "text": "You usually check revenue on Mondays",
        "subtitle": "Here's this week's performance",
        "action": "run",
        "query": "What was revenue this week?",
        "confidence": 0.92,
        "icon": "trending-up",
        "category": "Personalized"
    },
    {
        "type": "popular",
        "text": "Top products by sales",
        "subtitle": "Most asked by your team",
        "action": "suggest",
        "query": "What are the top 10 products by sales this month?",
        "confidence": 0.85,
        "icon": "bar-chart",
        "category": "Popular"
    },
    {
        "type": "trending",
        "text": "Customer churn analysis",
        "subtitle": "Rising interest in your organization",
        "action": "suggest",
        "query": "Analyze customer churn patterns",
        "confidence": 0.78,
        "icon": "users",
        "category": "Trending"
    },
    {
        "type": "recent",
        "text": "Q4 Marketing ROI",
        "subtitle": "Last viewed 2 hours ago",
        "action": "open",
        "query": "What was the ROI on Q4 marketing campaigns?",
        "confidence": 0.95,
        "icon": "clock",
        "category": "Recent"
    },
    {
        "type": "pattern",
        "text": "Monthly team performance",
        "subtitle": "You check this every month end",
        "action": "run",
        "query": "Show me team performance metrics for this month",
        "confidence": 0.88,
        "icon": "target",
        "category": "Personalized"
    }
]


@router.get("", response_model=SuggestionsListResponse)
async def get_suggestions(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(5, ge=1, le=20, description="Number of suggestions to return")
):
    """
    Get personalized suggestions for the user
    
    Returns AI-generated suggestions based on user patterns,
    popular queries, and recent activity.
    """
    try:
        logger.info(f"Fetching suggestions - category: {category}, limit: {limit}")
        
        # Filter by category if provided
        suggestions = MOCK_SUGGESTIONS
        if category:
            suggestions = [s for s in suggestions if s.get("category", "").lower() == category.lower()]
        
        # Limit results
        suggestions = suggestions[:limit]
        
        # Convert to Pydantic models
        suggestion_models = [SuggestionResponse(**s) for s in suggestions]
        
        return SuggestionsListResponse(
            suggestions=suggestion_models,
            total=len(suggestion_models),
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate suggestions: {str(e)}"
        )


@router.get("/categories", response_model=List[str])
async def get_suggestion_categories():
    """Get available suggestion categories"""
    categories = list(set(s.get("category", "General") for s in MOCK_SUGGESTIONS))
    return sorted(categories)


@router.get("/history/search", response_model=List[HistoryItem])
async def search_history(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search question history with semantic matching
    
    Searches through user's query history and returns
    matching results sorted by relevance.
    """
    try:
        logger.info(f"Searching history for: {q}")
        
        # Mock history data - in production this would search a vector DB
        mock_history = [
            HistoryItem(
                id="hist-1",
                query="Revenue by region last quarter",
                timestamp=datetime.utcnow(),
                result_count=5,
                is_favorite=True
            ),
            HistoryItem(
                id="hist-2",
                query="Top customers by lifetime value",
                timestamp=datetime.utcnow(),
                result_count=10,
                is_favorite=False
            ),
            HistoryItem(
                id="hist-3",
                query="Monthly growth rates",
                timestamp=datetime.utcnow(),
                result_count=12,
                is_favorite=False
            ),
        ]
        
        # Simple text matching for demo
        filtered = [
            h for h in mock_history 
            if q.lower() in h.query.lower()
        ]
        
        return filtered[:limit]
        
    except Exception as e:
        logger.error(f"Error searching history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search history: {str(e)}"
        )


@router.post("/feedback")
async def submit_suggestion_feedback(
    suggestion_id: str,
    was_helpful: bool,
    feedback_text: Optional[str] = None
):
    """
    Submit feedback on a suggestion
    
    Used to improve future suggestion quality.
    """
    logger.info(f"Suggestion feedback - id: {suggestion_id}, helpful: {was_helpful}")
    
    # In production, store this feedback for model improvement
    return {
        "status": "recorded",
        "suggestion_id": suggestion_id,
        "timestamp": datetime.utcnow().isoformat()
    }
