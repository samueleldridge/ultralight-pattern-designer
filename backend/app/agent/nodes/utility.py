from typing import Literal
from app.agent.state import AgentState


async def ask_clarification_node(state: AgentState) -> AgentState:
    """Ask user for clarification"""
    
    state["current_step"] = "ask_clarification"
    state["step_message"] = state.get("clarification_question", "Please provide more details")
    state["step_status"] = "complete"
    state["needs_clarification"] = True
    
    return state


async def end_node(state: AgentState) -> AgentState:
    """Mark workflow as complete"""
    
    state["current_step"] = "end"
    state["step_message"] = "Complete"
    state["step_status"] = "complete"
    
    return state


def should_investigate(state: AgentState) -> Literal["investigate", "generate_viz"]:
    """Determine if more investigation is needed"""
    
    # If intent was investigate and we haven't completed investigation
    if state.get("intent") == "investigate" and not state.get("investigation_complete"):
        return "investigate"
    
    return "generate_viz"
