import json
import aiosqlite
from typing import Dict, Any
from app.agent.state import AgentState
from app.config import get_settings

settings = get_settings()

# Use SQLite for local development (PostgreSQL in production)
DEMO_DATABASE_URL = settings.database_url if hasattr(settings, 'database_url') else "sqlite+aiosqlite:///./test.db"

# Extract path from SQLite URL
def get_sqlite_path(url: str) -> str:
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite:///", "")
    return "./test.db"


async def execute_sql_node(state: AgentState) -> AgentState:
    """Execute SQL against database (SQLite for local dev)"""
    
    state["current_step"] = "execute_sql"
    state["step_message"] = "Executing query..."
    state["step_status"] = "in_progress"
    
    sql = state.get("sql", "")
    
    if not sql or sql.strip() == "":
        state["execution_error"] = "No SQL generated"
        state["step_status"] = "error"
        return state
    
    try:
        # Get database path
        db_path = get_sqlite_path(DEMO_DATABASE_URL)
        
        # Connect to SQLite database
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        
        # Execute query
        cursor = await conn.execute(sql)
        rows = await cursor.fetchall()
        
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
