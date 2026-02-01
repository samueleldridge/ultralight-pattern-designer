import json
import asyncpg
from typing import Dict, Any
from app.agent.state import AgentState
from app.config import get_settings

settings = get_settings()

# Demo database connection (same as app DB for MVP)
# In production, this would use customer-provided connection strings
DEMO_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/aianalytics"


async def execute_sql_node(state: AgentState) -> AgentState:
    """Execute SQL against database"""
    
    state["current_step"] = "execute_sql"
    state["step_message"] = "Executing query..."
    state["step_status"] = "in_progress"
    
    sql = state.get("sql", "")
    
    if not sql or sql.strip() == "":
        state["execution_error"] = "No SQL generated"
        state["step_status"] = "error"
        return state
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DEMO_DATABASE_URL)
        
        # Set timeout
        await conn.execute("SET statement_timeout = '30000'")  # 30 seconds
        
        # Execute query
        rows = await conn.fetch(sql)
        
        # Convert to dict
        results = [dict(row) for row in rows]
        
        state["execution_result"] = {
            "rows": results[:1000],  # Limit results
            "row_count": len(results),
            "columns": list(results[0].keys()) if results else []
        }
        state["step_status"] = "complete"
        
        await conn.close()
        
    except Exception as e:
        state["execution_error"] = str(e)
        state["step_status"] = "error"
    
    return state


def execution_router(state: AgentState):
    """Route based on execution result"""
    from typing import Literal
    if state.get("execution_result"):
        return "analyze_results"
    return "analyze_error"
