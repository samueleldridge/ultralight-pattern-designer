from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class InsightResponse(BaseModel):
    """Proactive insight response"""
    id: str
    type: str
    title: str
    description: Optional[str] = None
    suggested_query: Optional[str] = None
    created_at: str


class QueryRequest(BaseModel):
    """Natural language query request"""
    question: str
    connection_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Query response"""
    id: str
    question: str
    sql: Optional[str] = None
    results: Optional[List[Dict]] = None
    visualization: Optional[Dict] = None
    summary: Optional[str] = None
    error: Optional[str] = None


class StreamEvent(BaseModel):
    """Streaming event for real-time updates"""
    step: str
    status: str  # pending, in_progress, completed, error
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class DashboardCreate(BaseModel):
    """Create dashboard request"""
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class DashboardResponse(BaseModel):
    """Dashboard response"""
    id: str
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None


class ViewCreate(BaseModel):
    """Create view request"""
    name: str
    view_type: str
    config: Optional[Dict[str, Any]] = None
    query_sql: Optional[str] = None


class ViewResponse(BaseModel):
    """View response"""
    id: str
    dashboard_id: str
    name: str
    view_type: str
    config: Optional[Dict[str, Any]] = None
    created_at: str


class SuggestionResponse(BaseModel):
    """Suggestion response"""
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    confidence: Optional[float] = None
