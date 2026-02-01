import re
from typing import Literal
from app.agent.state import AgentState


async def validate_sql_node(state: AgentState) -> AgentState:
    """Validate generated SQL before execution"""
    
    state["current_step"] = "validate_sql"
    state["step_message"] = "Validating query..."
    state["step_status"] = "in_progress"
    
    sql = state.get("sql", "")
    errors = []
    
    # 1. Safety checks (MUST pass)
    dangerous_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER']
    sql_upper = sql.upper()
    
    for keyword in dangerous_keywords:
        if re.search(rf'\b{keyword}\b', sql_upper):
            errors.append(f"Query contains forbidden keyword: {keyword}")
    
    # 2. Syntax check (basic)
    if not sql.strip().upper().startswith('SELECT'):
        errors.append("Query must start with SELECT")
    
    # 3. Check for required components
    if 'FROM' not in sql_upper:
        errors.append("Query missing FROM clause")
    
    if errors:
        state["sql_valid"] = False
        state["validation_error"] = "; ".join(errors)
        state["step_status"] = "error"
    else:
        state["sql_valid"] = True
        state["validation_error"] = None
        state["step_status"] = "complete"
    
    return state


def validation_router(state: AgentState) -> Literal["execute", "analyze_error"]:
    """Route based on validation result"""
    return "execute" if state.get("sql_valid") else "analyze_error"
