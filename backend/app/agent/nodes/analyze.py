import json
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.5,
    api_key=settings.openai_api_key
)


async def analyze_results_node(state: AgentState) -> AgentState:
    """Analyze query results and generate insights"""
    
    state["current_step"] = "analyze_results"
    state["step_message"] = "Analyzing results..."
    state["step_status"] = "in_progress"
    
    result = state.get("execution_result", {})
    rows = result.get("rows", [])
    query = state.get("query", "")
    
    if not rows:
        state["insights"] = "No data found for this query."
        state["follow_up_suggestions"] = [
            "Try a broader time range",
            "Check if filters are too restrictive"
        ]
        state["step_status"] = "complete"
        return state
    
    # Build analysis prompt
    data_sample = json.dumps(rows[:10], indent=2)
    
    prompt = f"""Analyze these query results and generate insights.

Question: "{query}"

Results (first 10 rows):
{data_sample}

Total rows: {len(rows)}

Provide:
1. A brief summary of what the data shows
2. Key insights or patterns
3. 3 follow-up questions the user might want to ask

Respond with JSON:
{{
    "summary": "...",
    "insights": ["...", "..."],
    "follow_ups": ["...", "...", "..."]
}}"""
    
    response = await llm.ainvoke(prompt)
    
    try:
        result = json.loads(response.content)
        state["insights"] = result.get("summary", "")
        state["follow_up_suggestions"] = result.get("follow_ups", [])
    except:
        state["insights"] = f"Query returned {len(rows)} results."
        state["follow_up_suggestions"] = [
            "Can you break this down by category?",
            "What was this like last month?",
            "Show me the top 10 items"
        ]
    
    state["step_status"] = "complete"
    return state


async def generate_viz_node(state: AgentState) -> AgentState:
    """Generate visualization configuration"""
    
    state["current_step"] = "generate_viz"
    state["step_message"] = "Generating visualization..."
    state["step_status"] = "in_progress"
    
    result = state.get("execution_result", {})
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    
    # Auto-detect chart type if not specified
    viz_config = state.get("visualization_config", {})
    chart_type = viz_config.get("type", "table")
    
    # Detect time series
    time_cols = [c for c in columns if any(t in c.lower() for t in ['date', 'time', 'month', 'day'])]
    numeric_cols = [c for c in columns if isinstance(rows[0].get(c), (int, float))] if rows else []
    
    if time_cols and numeric_cols and chart_type == "table":
        chart_type = "line"
    elif len(numeric_cols) >= 1 and len(rows) <= 20 and chart_type == "table":
        chart_type = "bar"
    
    state["visualization_config"] = {
        "type": chart_type,
        "x_axis": time_cols[0] if time_cols else columns[0] if columns else None,
        "y_axis": numeric_cols[0] if numeric_cols else None,
        "title": state.get("query", "Results")[:50]
    }
    
    state["step_status"] = "complete"
    return state
