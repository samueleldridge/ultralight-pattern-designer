import json
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.3,
    api_key=settings.openai_api_key
)


async def analyze_error_node(state: AgentState) -> AgentState:
    """Analyze SQL error and suggest fixes"""
    
    state["current_step"] = "analyze_error"
    state["step_message"] = "Analyzing error..."
    state["step_status"] = "in_progress"
    
    error = state.get("validation_error") or state.get("execution_error", "")
    sql = state.get("sql", "")
    
    prompt = f"""You are a SQL expert. Analyze this error and suggest a fix.

SQL: {sql}
Error: {error}

Can this be fixed automatically? If yes, suggest the corrected SQL.
If no, explain what the user needs to clarify.

Respond with JSON:
{{
    "can_fix": true/false,
    "suggestion": "explanation or corrected SQL",
    "user_question": "if can_fix is false, what to ask the user"
}}"""
    
    response = await llm.ainvoke(prompt)
    
    try:
        result = json.loads(response.content)
        
        if result.get("can_fix") and state.get("retry_count", 0) < 3:
            # Try to fix
            state["sql"] = result.get("suggestion", sql)
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["sql_valid"] = True  # Reset to try again
            state["validation_error"] = None
        else:
            # Can't fix or max retries
            state["needs_clarification"] = True
            state["clarification_question"] = result.get("user_question", "Please clarify your question")
    
    except:
        state["needs_clarification"] = True
        state["clarification_question"] = "I encountered an error. Could you rephrase your question?"
    
    state["step_status"] = "complete"
    return state


def error_router(state: AgentState) -> Literal["generate_sql", "ask_clarification", "end"]:
    """Route after error analysis"""
    
    if state.get("needs_clarification"):
        return "ask_clarification"
    
    if state.get("retry_count", 0) < 3 and state.get("sql"):
        return "generate_sql"  # Retry with fix
    
    return "end"
