from typing import Literal
from app.agent.state import AgentState
from app.database.dialect import SQLValidator, SQLDialect


async def validate_sql_node(state: AgentState) -> AgentState:
    """Validate generated SQL with dialect awareness"""
    
    state["current_step"] = "validate_sql"
    state["step_message"] = "Validating query..."
    state["step_status"] = "in_progress"
    
    sql = state.get("sql", "")
    dialect = state.get("dialect", "postgresql")
    
    validator = SQLValidator(SQLDialect(dialect))
    validation = validator.validate(sql)
    
    state["sql_valid"] = validation["valid"]
    state["validation_error"] = "; ".join(validation["errors"]) if validation["errors"] else None
    state["validation_warnings"] = validation["warnings"]
    
    if validation["valid"]:
        state["step_status"] = "complete"
    else:
        state["step_status"] = "error"
    
    return state


def validation_router(state: AgentState) -> Literal["execute", "analyze_error"]:
    """Route based on validation result"""
    return "execute" if state.get("sql_valid") else "analyze_error"
