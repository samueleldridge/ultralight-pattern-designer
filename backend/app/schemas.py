from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """Query request schema"""
    query: str = Field(..., min_length=1, description="The natural language query")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    connection_id: Optional[str] = Field(None, description="Optional database connection ID")


class QueryResponse(BaseModel):
    """Query response schema"""
    workflow_id: str
    status: str
    message: str


class StreamEvent(BaseModel):
    """Stream event schema for SSE"""
    step: str
    status: str
    message: str
    icon: Optional[str] = None
    progress: Optional[int] = None
    category: Optional[str] = None
    timestamp: Optional[str] = None
    sql: Optional[str] = None
    result_preview: Optional[Dict[str, Any]] = None
    viz_config: Optional[Dict[str, Any]] = None
    insights: Optional[str] = None
    follow_ups: Optional[List[str]] = None
    error: Optional[str] = None


class SuggestionResponse(BaseModel):
    """Suggestion response schema - matches frontend expectations"""
    type: str = Field(..., description="Suggestion type: pattern, popular, trending, recent")
    text: str = Field(..., description="Main display text")
    subtitle: Optional[str] = Field(None, description="Secondary descriptive text")
    action: Optional[str] = Field(None, description="Action type: run, suggest, open")
    query: Optional[str] = Field(None, description="The query to execute or suggest")
    confidence: Optional[float] = Field(0.5, ge=0, le=1, description="Confidence score 0-1")
    icon: Optional[str] = Field(None, description="Icon identifier for UI")
    category: Optional[str] = Field(None, description="Category for grouping suggestions")


class SuggestionsListResponse(BaseModel):
    """Wrapper for suggestions list"""
    suggestions: List[SuggestionResponse]
    total: int
    generated_at: datetime


class HistoryItem(BaseModel):
    """History search result item"""
    id: str
    query: str
    timestamp: datetime
    result_count: Optional[int] = None
    is_favorite: bool = False


class InsightResponse(BaseModel):
    """Proactive insight response"""
    id: str
    type: str
    title: str
    description: Optional[str] = None
    suggested_query: Optional[str] = None
    created_at: str


class DashboardCreate(BaseModel):
    """Dashboard creation schema"""
    name: str
    description: Optional[str] = None
    is_default: Optional[bool] = False


class DashboardResponse(BaseModel):
    """Dashboard response schema"""
    id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ViewCreate(BaseModel):
    """View creation schema"""
    title: str
    query_text: str
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    chart_type: Optional[str] = "line"


class ViewResponse(BaseModel):
    """View response schema"""
    id: str
    title: str
    query_text: str
    position_x: int
    position_y: int
    width: int
    height: int
    chart_type: Optional[str] = None
    created_at: Optional[str] = None


class ConnectionCreate(BaseModel):
    """Connection creation schema"""
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    connection_type: str = "postgresql"


class ConnectionResponse(BaseModel):
    """Connection response schema"""
    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    connection_type: str
    status: str
    created_at: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str = "0.1.0"
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)
