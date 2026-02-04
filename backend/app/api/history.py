"""
Query History API Endpoints

Provides:
- GET /api/history - Recent queries
- GET /api/history/search - Semantic search
- GET /api/history/popular - Popular queries
- GET /api/history/similar - Similar to current query
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from app.services.query_history import get_query_history_service, QueryRecord
from app.middleware import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


class QueryHistoryItem(BaseModel):
    """Query history item response"""
    id: str
    query: str
    sql: Optional[str]
    result_summary: Optional[str]
    created_at: datetime
    execution_time_ms: Optional[int]


class PopularQueryItem(BaseModel):
    """Popular query item"""
    query: str
    count: int


class SimilarQueryRequest(BaseModel):
    """Request for similar queries"""
    query: str
    limit: int = 5


@router.get("", response_model=List[QueryHistoryItem])
async def get_recent_queries(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent queries for the current user.
    
    Returns the most recent queries with optional time filtering.
    """
    service = get_query_history_service()
    
    records = await service.get_recent_queries(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit,
        days=days
    )
    
    return [
        QueryHistoryItem(
            id=r.id,
            query=r.query,
            sql=r.sql,
            result_summary=r.result_summary,
            created_at=r.created_at,
            execution_time_ms=r.execution_time_ms
        )
        for r in records
    ]


@router.get("/search")
async def search_queries(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """
    Search query history using semantic similarity.
    
    Finds queries similar to the search term using embeddings.
    """
    service = get_query_history_service()
    
    records = await service.search_similar_queries(
        query=q,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    
    return {
        "query": q,
        "results": [
            {
                "id": r.id,
                "query": r.query,
                "sql": r.sql,
                "created_at": r.created_at.isoformat(),
                "similarity": "high"  # Simplified for MVP
            }
            for r in records
        ]
    }


@router.post("/similar")
async def find_similar_queries(
    request: SimilarQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Find queries similar to the provided query.
    
    Used for suggesting similar past queries in the chat interface.
    """
    service = get_query_history_service()
    
    records = await service.search_similar_queries(
        query=request.query,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=request.limit
    )
    
    return {
        "original_query": request.query,
        "similar_queries": [
            {
                "id": r.id,
                "query": r.query,
                "result_summary": r.result_summary
            }
            for r in records
        ]
    }


@router.get("/popular", response_model=List[PopularQueryItem])
async def get_popular_queries(
    limit: int = Query(10, ge=1, le=20),
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """
    Get most popular queries in the tenant.
    
    Returns frequently asked queries, useful for discovering
    common analytics patterns.
    """
    service = get_query_history_service()
    
    popular = await service.get_popular_queries(
        tenant_id=current_user["tenant_id"],
        limit=limit,
        days=days
    )
    
    return [PopularQueryItem(**item) for item in popular]


@router.get("/suggestions")
async def get_query_suggestions(
    query: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """
    Get autocomplete suggestions based on query history.
    
    Returns queries that start with or contain the partial query.
    """
    service = get_query_history_service()
    
    # Get recent queries
    recent = await service.get_recent_queries(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=50
    )
    
    # Filter by partial match
    query_lower = query.lower()
    suggestions = [
        r for r in recent
        if query_lower in r.query.lower()
    ][:limit]
    
    return {
        "partial": query,
        "suggestions": [
            {
                "id": r.id,
                "query": r.query,
                "highlighted": r.query.replace(
                    query, f"**{query}**"
                ) if query_lower in r.query.lower() else r.query
            }
            for r in suggestions
        ]
    }
