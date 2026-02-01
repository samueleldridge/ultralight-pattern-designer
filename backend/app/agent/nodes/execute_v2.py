from typing import Dict, Any, Literal
from app.agent.state import AgentState
from app.database.connector import DatabaseConfig
from app.database.executor import QueryExecutor


async def execute_sql_node(state: AgentState) -> AgentState:
    """Execute SQL using the query executor with caching"""
    
    state["current_step"] = "execute_sql"
    state["step_message"] = "Executing query..."
    state["step_status"] = "in_progress"
    
    sql = state.get("sql", "")
    
    # Build database config from connection info
    # For MVP, use demo connection
    config = DatabaseConfig(
        db_type=state.get("dialect", "postgresql"),
        host="postgres",
        port=5432,
        database="aianalytics",
        username="postgres",
        password="postgres"
    )
    
    executor = QueryExecutor()
    
    try:
        result = await executor.execute(
            query=sql,
            config=config,
            use_cache=True,
            timeout_seconds=30
        )
        
        if result["success"]:
            state["execution_result"] = result["data"]
            state["execution_warnings"] = result.get("warnings", [])
            state["from_cache"] = result.get("from_cache", False)
            state["step_status"] = "complete"
        else:
            state["execution_error"] = result.get("error", "Unknown error")
            state["execution_suggestion"] = result.get("suggestion", "")
            state["step_status"] = "error"
            
    except Exception as e:
        state["execution_error"] = str(e)
        state["step_status"] = "error"
    
    return state


def execution_router(state: AgentState) -> Literal["analyze_results", "analyze_error"]:
    """Route based on execution result"""
    return "analyze_results" if state.get("execution_result") else "analyze_error"
