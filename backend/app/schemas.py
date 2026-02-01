

class InsightResponse(BaseModel):
    """Proactive insight response"""
    id: str
    type: str
    title: str
    description: Optional[str] = None
    suggested_query: Optional[str] = None
    created_at: str
