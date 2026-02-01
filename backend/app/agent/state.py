from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from operator import add


class AgentState(TypedDict):
    """State for the agent workflow"""
    
    # Input
    query: str
    tenant_id: str
    user_id: str
    connection_id: Optional[str]
    
    # Context (built up during workflow)
    user_context: Optional[Dict]  # User profile, preferences
    schema_context: Optional[Dict]  # Relevant tables/columns
    few_shot_examples: Optional[List]  # Similar past queries
    semantic_definitions: Optional[Dict]  # Business terms
    
    # Workflow routing
    intent: Optional[str]  # 'simple', 'complex', 'investigate', 'clarify'
    needs_clarification: bool
    clarification_question: Optional[str]
    
    # SQL generation
    sql: Optional[str]
    sql_valid: bool
    validation_error: Optional[str]
    retry_count: int
    
    # Execution
    execution_result: Optional[Dict]
    execution_error: Optional[str]
    
    # Investigation (for complex queries)
    investigation_history: Annotated[List[Dict], add]
    investigation_complete: bool
    
    # Output
    visualization_config: Optional[Dict]
    insights: Optional[str]
    follow_up_suggestions: Optional[List[str]]
    
    # Streaming
    current_step: Optional[str]
    step_message: Optional[str]
    step_status: Optional[str]  # 'started', 'in_progress', 'complete', 'error'
    
    # Meta
    workflow_id: str
    started_at: Optional[str]
    completed_at: Optional[str]
