from pydantic import BaseModel, Field
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
    query: str  # Changed from 'question' to match test expectations
    tenant_id: str
    user_id: str
    connection_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Query response"""
    workflow_id: str  # Changed from 'id' to match test expectations
    status: str
    message: str
    rate_limit: Optional[Dict[str, Any]] = None


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
    title: str  # Changed from 'name' to match test expectations
    query_text: str  # Changed from 'query_sql' to match test expectations
    position_x: int = Field(0, ge=0)
    position_y: int = Field(0, ge=0)
    width: int = Field(6, ge=1)
    height: int = Field(4, ge=1)
    chart_type: Optional[str] = "table"
    config: Optional[Dict[str, Any]] = None


class ViewResponse(BaseModel):
    """View response"""
    id: str
    title: str  # Changed from 'name' to match test expectations
    query_text: Optional[str] = None  # Changed from 'query_sql' to match test expectations
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    chart_type: Optional[str] = "table"
    config: Optional[Dict[str, Any]] = None


class SuggestionResponse(BaseModel):
    """Suggestion response"""
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    confidence: Optional[float] = None


class SuggestionItem(BaseModel):
    """Individual suggestion item for list endpoints"""
    type: str
    text: str
    action: str
    query: str
