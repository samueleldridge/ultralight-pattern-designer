"""
Enhanced Analysis Node

Features:
- Natural language summaries
- Insight generation with comparative analysis
- Anomaly detection
- Follow-up suggestions
"""

import json
from typing import Dict, List, Optional, Any
from app.llm_provider import get_llm_provider
from app.agent.state import AgentState
from app.nlp.response_formatting import format_query_response, generate_insights
from app.nlp.context_management import save_query_context, get_session_manager
from app.nlp.query_suggestions import record_query_for_suggestions

llm_provider = get_llm_provider()


async def analyze_results_node_enhanced(state: AgentState) -> AgentState:
    """
    Enhanced results analysis with insights, comparisons, and recommendations.
    """
    
    state["current_step"] = "analyze_results"
    state["step_message"] = "Analyzing results and generating insights..."
    state["step_status"] = "in_progress"
    
    try:
        result = state.get("execution_result", {})
        query = state.get("resolved_query", state.get("query", ""))
        
        # Check if we have results
        rows = result.get("rows", [])
        if not rows:
            state["insights"] = "No data found for this query."
            state["follow_up_suggestions"] = [
                {
                    "question": "Try a broader time range",
                    "type": "suggestion"
                },
                {
                    "question": "Check if filters are too restrictive",
                    "type": "suggestion"
                }
            ]
            state["step_status"] = "complete"
            return state
        
        # Get previous results for comparison
        previous_results = await _get_previous_results(state)
        
        # Format response with insights
        formatted_response = await format_query_response(
            query=query,
            results=result,
            previous_results=previous_results,
            user_preferences=state.get("user_context")
        )
        
        # Store insights
        state["insights"] = formatted_response.get("executive_summary", "")
        state["detailed_response"] = formatted_response.get("detailed_response", "")
        state["key_insights"] = formatted_response.get("insights", [])
        state["comparisons"] = formatted_response.get("comparisons", [])
        state["anomalies_detected"] = formatted_response.get("anomalies", [])
        
        # Store follow-up suggestions
        state["follow_up_suggestions"] = formatted_response.get(
            "follow_up_suggestions", []
        )
        
        # Generate additional query suggestions
        from app.nlp.query_suggestions import get_query_suggestions
        suggestions = await get_query_suggestions(
            partial_query=query,
            user_id=state["user_id"],
            conversation_context=formatted_response.get("follow_up_suggestions", [])
        )
        state["query_suggestions"] = suggestions
        
        # Save context for future queries
        query_id = save_query_context(
            session_id=state.get("workflow_id", "default"),
            query=query,
            entities=state.get("extracted_entities", {}),
            sql=state.get("sql"),
            results_summary={
                "row_count": len(rows),
                "columns": result.get("columns", []),
                "summary": formatted_response.get("data_summary", {})
            },
            visualization_type=state.get("visualization_config", {}).get("type"),
            insights=[i.get("title", "") for i in formatted_response.get("insights", [])],
            intent=state.get("intent")
        )
        
        state["query_id"] = query_id
        
        # Record for suggestion learning
        record_query_for_suggestions(
            user_id=state["user_id"],
            query=query,
            intent=state.get("intent")
        )
        
        state["step_status"] = "complete"
        state["step_message"] = "Analysis complete"
        
    except Exception as e:
        # Fallback analysis
        rows = state.get("execution_result", {}).get("rows", [])
        state["insights"] = f"Query returned {len(rows)} results."
        state["follow_up_suggestions"] = [
            {"question": "Can you break this down by category?", "type": "breakdown"},
            {"question": "Show me this over time", "type": "trend"},
            {"question": "What was this last month?", "type": "comparison"}
        ]
        state["step_status"] = "complete"
        state["error"] = f"Analysis warning: {str(e)}"
    
    return state


async def generate_viz_node_enhanced(state: AgentState) -> AgentState:
    """
    Enhanced visualization generation with smart defaults.
    """
    
    state["current_step"] = "generate_viz"
    state["step_message"] = "Configuring visualization..."
    state["step_status"] = "in_progress"
    
    try:
        result = state.get("execution_result", {})
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows or not columns:
            state["visualization_config"] = {"type": "table"}
            state["step_status"] = "complete"
            return state
        
        # Get existing config or create new
        viz_config = state.get("visualization_config", {})
        chart_type = viz_config.get("type", "table")
        
        # Auto-detect chart type if not specified
        if chart_type == "table":
            chart_type = _detect_chart_type(rows, columns)
        
        # Detect columns for visualization
        time_cols = [
            c for c in columns 
            if any(t in c.lower() for t in ['date', 'time', 'day', 'month', 'year', 'week'])
        ]
        
        numeric_cols = []
        for c in columns:
            if rows and isinstance(rows[0], dict):
                val = rows[0].get(c)
                if isinstance(val, (int, float)):
                    numeric_cols.append(c)
        
        category_cols = [
            c for c in columns 
            if c not in time_cols and c not in numeric_cols
        ]
        
        # Build enhanced viz config
        viz_config = {
            "type": chart_type,
            "title": _generate_chart_title(state),
            "x_axis": viz_config.get("x_axis") or (time_cols[0] if time_cols else 
                                                    (category_cols[0] if category_cols else None)),
            "y_axis": viz_config.get("y_axis") or (numeric_cols[0] if numeric_cols else None),
            "category": category_cols[0] if category_cols else None,
            "time_column": time_cols[0] if time_cols else None,
            "explanation": viz_config.get("explanation", ""),
            "row_count": len(rows),
            "recommendations": _get_viz_recommendations(chart_type, rows, columns)
        }
        
        state["visualization_config"] = viz_config
        state["step_status"] = "complete"
        state["step_message"] = "Visualization configured"
        
    except Exception as e:
        state["visualization_config"] = {"type": "table"}
        state["step_status"] = "complete"
        state["error"] = f"Visualization warning: {str(e)}"
    
    return state


def _detect_chart_type(rows: List[Dict], columns: List[str]) -> str:
    """Auto-detect the best chart type for the data"""
    
    if not rows:
        return "table"
    
    # Check for time series
    has_time = any(
        any(t in c.lower() for t in ['date', 'time', 'day', 'month'])
        for c in columns
    )
    
    # Count numeric columns
    numeric_cols = []
    if rows and isinstance(rows[0], dict):
        for c in columns:
            val = rows[0].get(c)
            if isinstance(val, (int, float)):
                numeric_cols.append(c)
    
    # Determine chart type
    if has_time and len(numeric_cols) >= 1:
        if len(numeric_cols) > 1:
            return "line"  # Multi-series line chart
        return "line"
    
    if len(rows) <= 5 and len(numeric_cols) >= 1:
        return "pie"  # Good for small category sets
    
    if len(rows) <= 20 and len(numeric_cols) >= 1:
        return "bar"
    
    if len(numeric_cols) >= 2:
        return "scatter"
    
    return "table"


def _generate_chart_title(state: AgentState) -> str:
    """Generate a descriptive chart title"""
    
    query = state.get("query", "Results")
    intent = state.get("intent", "")
    
    # Clean up query for title
    title = query.replace("Show me ", "").replace("What is ", "").replace("the ", "")
    title = title[0].upper() + title[1:] if title else "Results"
    
    # Add time context if available
    entities = state.get("extracted_entities", {})
    time_range = entities.get("time_range", {})
    if time_range and time_range.get("description"):
        title += f" ({time_range['description']})"
    
    return title[:60]  # Limit length


def _get_viz_recommendations(chart_type: str, rows: List[Dict], columns: List[str]) -> List[str]:
    """Get visualization recommendations"""
    
    recommendations = []
    
    if chart_type == "table" and len(rows) > 50:
        recommendations.append("Consider filtering or aggregating - large datasets work better with charts")
    
    if chart_type == "pie" and len(rows) > 7:
        recommendations.append("Pie charts work best with 5-7 categories - consider a bar chart")
    
    if len(columns) > 5:
        recommendations.append("Many columns detected - consider hiding less important ones")
    
    return recommendations


async def _get_previous_results(state: AgentState) -> Optional[Dict]:
    """Get previous query results for comparison"""
    
    session_manager = get_session_manager()
    session = session_manager.get_or_create_session(
        session_id=state.get("workflow_id", "default"),
        user_id=state["user_id"],
        tenant_id=state["tenant_id"]
    )
    
    # Get most recent previous query
    recent = session.get_recent(2)  # Get 2, we'll use the older one
    if len(recent) >= 2:
        prev_context = recent[0]  # The one before current
        if prev_context.results_summary:
            return prev_context.results_summary
    
    return None
