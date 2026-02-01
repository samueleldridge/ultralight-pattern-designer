"""
Enhanced Agent Workflow

Integrates all NLP enhancements:
- Enhanced intent classification with ambiguity detection
- Schema-aware SQL generation with few-shot examples
- Context management for multi-turn conversations
- Enhanced analysis with insights and comparisons
"""

from langgraph.graph import StateGraph, END
from app.agent.state import AgentState

# Enhanced nodes
from app.agent.nodes.classify_enhanced import classify_intent_node, router
from app.agent.nodes.context import fetch_context_node
from app.agent.nodes.generate_enhanced import generate_sql_node_enhanced, generate_sql_with_retry
from app.agent.nodes.validate import validate_sql_node, validation_router
from app.agent.nodes.execute import execute_sql_node, execution_router
from app.agent.nodes.error import analyze_error_node, error_router
from app.agent.nodes.analyze_enhanced import analyze_results_node_enhanced, generate_viz_node_enhanced
from app.agent.nodes.utility import ask_clarification_node, end_node


def create_enhanced_workflow():
    """
    Create the enhanced agent workflow with all NLP improvements.
    """
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add enhanced nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("fetch_context", fetch_context_node)
    workflow.add_node("generate_sql", generate_sql_with_retry)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("analyze_error", analyze_error_node)
    workflow.add_node("analyze_results", analyze_results_node_enhanced)
    workflow.add_node("generate_viz", generate_viz_node_enhanced)
    workflow.add_node("ask_clarification", ask_clarification_node)
    workflow.add_node("end", end_node)
    
    # Add edges
    workflow.set_entry_point("classify_intent")
    
    # From classify, route based on intent
    workflow.add_conditional_edges(
        "classify_intent",
        router,
        {
            "fetch_context": "fetch_context",
            "ask_clarification": "ask_clarification"
        }
    )
    
    # From fetch context, always go to generate
    workflow.add_edge("fetch_context", "generate_sql")
    
    # From generate, validate
    workflow.add_edge("generate_sql", "validate_sql")
    
    # From validate, route based on result
    workflow.add_conditional_edges(
        "validate_sql",
        validation_router,
        {
            "execute": "execute_sql",
            "analyze_error": "analyze_error"
        }
    )
    
    # From execute, route based on result
    workflow.add_conditional_edges(
        "execute_sql",
        execution_router,
        {
            "analyze_results": "analyze_results",
            "analyze_error": "analyze_error"
        }
    )
    
    # From error analysis, retry or clarify
    workflow.add_conditional_edges(
        "analyze_error",
        error_router,
        {
            "generate_sql": "generate_sql",
            "ask_clarification": "ask_clarification",
            "end": "end"
        }
    )
    
    # From analyze results, generate visualization
    workflow.add_edge("analyze_results", "generate_viz")
    
    # From generate viz, end
    workflow.add_edge("generate_viz", "end")
    
    # Clarification ends workflow (user must restart)
    workflow.add_edge("ask_clarification", END)
    workflow.add_edge("end", END)
    
    # Compile
    app = workflow.compile()
    
    return app


# Global workflow instance
enhanced_workflow_app = create_enhanced_workflow()
