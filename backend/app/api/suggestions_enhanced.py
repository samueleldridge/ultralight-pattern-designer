"""
Enhanced Suggestions API

Provides intelligent query suggestions with:
- Auto-complete
- Did-you-mean corrections
- Template suggestions
- Related queries
- Next-step suggestions
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas import SuggestionResponse
from app.nlp.query_suggestions import (
    get_query_suggestions,
    find_similar_past_queries,
    get_suggestion_engine
)
from app.nlp.entity_extraction import DateParser

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., description="Partial query to complete"),
    user_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10)
):
    """
    Get auto-complete suggestions for a partial query.
    
    Example: /api/suggestions/autocomplete?q=show me rev
    """
    suggestions = await get_query_suggestions(
        partial_query=q,
        user_id=user_id
    )
    
    completions = suggestions.get("auto_completions", [])[:limit]
    
    return {
        "query": q,
        "suggestions": [
            {
                "text": c["text"],
                "highlight": c.get("highlight", ""),
                "category": c.get("category", "general")
            }
            for c in completions
        ]
    }


@router.get("/did-you-mean")
async def did_you_mean(
    q: str = Query(..., description="Query to check for corrections"),
    user_id: Optional[str] = Query(None)
):
    """
    Get 'did you mean' suggestions for potential typos or improvements.
    
    Example: /api/suggestions/did-you-mean?q=reveune last month
    """
    suggestions = await get_query_suggestions(
        partial_query=q,
        user_id=user_id
    )
    
    corrections = suggestions.get("did_you_mean", [])
    
    return {
        "query": q,
        "corrections": [
            {
                "original": c["original"],
                "suggestion": c["suggestion"],
                "reason": c.get("reason", "")
            }
            for c in corrections
        ],
        "has_corrections": len(corrections) > 0
    }


@router.get("/templates")
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(5, ge=1, le=10)
):
    """
    Get available query templates.
    
    Categories: trend, breakdown, ranking, comparison, filtered, analysis, summary, average
    
    Example: /api/suggestions/templates?category=ranking
    """
    engine = get_suggestion_engine()
    
    templates = [
        t for t in engine.TEMPLATES
        if category is None or t.category == category
    ]
    
    return {
        "templates": [
            {
                "name": t.name,
                "template": t.template,
                "example": t.example,
                "category": t.category,
                "description": t.description,
                "variables": t.variables
            }
            for t in templates[:limit]
        ]
    }


@router.get("/related")
async def related_queries(
    q: str = Query(..., description="Query to find related suggestions for"),
    user_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10)
):
    """
    Get related query suggestions based on the current query.
    
    Example: /api/suggestions/related?q=revenue by product
    """
    suggestions = await get_query_suggestions(
        partial_query=q,
        user_id=user_id
    )
    
    related = suggestions.get("related_queries", [])[:limit]
    
    return {
        "query": q,
        "related": [
            {
                "query": r.get("query", ""),
                "context": r.get("context", "")
            }
            for r in related
        ]
    }


@router.get("/next-steps")
async def next_steps(
    q: str = Query(..., description="Current query to get follow-ups for"),
    user_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10)
):
    """
    Get suggested next-step queries (follow-ups).
    
    Example: /api/suggestions/next-steps?q=What was revenue this month?
    """
    suggestions = await get_query_suggestions(
        partial_query=q,
        user_id=user_id
    )
    
    next_steps_list = suggestions.get("next_steps", [])[:limit]
    
    return {
        "query": q,
        "next_steps": [
            {
                "query": n.get("query", ""),
                "based_on": n.get("based_on", "")
            }
            for n in next_steps_list
        ]
    }


@router.get("/all")
async def get_all_suggestions(
    q: str = Query(..., description="Query to get suggestions for"),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all types of suggestions in a single request.
    
    Returns: auto-completions, did-you-mean, templates, related, and next-steps.
    
    Example: /api/suggestions/all?q=show me sales
    """
    suggestions = await get_query_suggestions(
        partial_query=q,
        user_id=user_id
    )
    
    return {
        "query": q,
        "auto_completions": suggestions.get("auto_completions", []),
        "did_you_mean": suggestions.get("did_you_mean", []),
        "templates": suggestions.get("templates", []),
        "related_queries": suggestions.get("related_queries", []),
        "next_steps": suggestions.get("next_steps", [])
    }


@router.get("/similar")
async def similar_queries(
    q: str = Query(..., description="Query to find similar past queries for"),
    user_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=10)
):
    """
    Find similar past queries from the user's history.
    
    Example: /api/suggestions/similar?q=revenue analysis
    """
    similar = find_similar_past_queries(q, user_id, limit)
    
    return {
        "query": q,
        "similar_queries": [
            {
                "query": s.get("query", ""),
                "similarity": s.get("similarity", 0),
                "timestamp": s.get("timestamp")
            }
            for s in similar
        ]
    }


@router.get("/popular")
async def popular_queries(
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20)
):
    """
    Get popular queries across all users.
    
    Example: /api/suggestions/popular?category=trend
    """
    engine = get_suggestion_engine()
    popular = engine.get_popular_queries(category, limit)
    
    return {
        "popular": [
            {
                "query": p.get("query", ""),
                "category": p.get("category", "general"),
                "count": p.get("count", 0)
            }
            for p in popular
        ]
    }


@router.get("/time-parsing")
async def parse_time_expression(
    expression: str = Query(..., description="Time expression to parse")
):
    """
    Parse a natural language time expression.
    
    Example: /api/suggestions/time-parsing?expression=last+3+months
    """
    time_range = DateParser.parse(expression)
    
    if time_range:
        return {
            "expression": expression,
            "parsed": {
                "type": time_range.type,
                "description": time_range.description,
                "start_date": time_range.start_date.isoformat() if time_range.start_date else None,
                "end_date": time_range.end_date.isoformat() if time_range.end_date else None,
                "grain": time_range.grain,
                "confidence": time_range.confidence
            }
        }
    
    return {
        "expression": expression,
        "parsed": None,
        "error": "Could not parse time expression"
    }
