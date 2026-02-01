import json
from typing import Literal
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.agent.state import AgentState

settings = get_settings()

# Initialize LLM
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.1,
    api_key=settings.openai_api_key
)


async def classify_intent_node(state: AgentState) -> AgentState:
    """Classify the user's intent to route appropriately"""
    
    state["current_step"] = "classify_intent"
    state["step_message"] = "Understanding your question..."
    state["step_status"] = "in_progress"
    
    prompt = f"""Analyze this question and classify the intent:

Question: "{state['query']}"

Classify as one of:
- "simple": Direct lookup (single metric, specific time range)
- "complex": Analysis requiring multiple joins/aggregations
- "investigate": Exploratory ("why", "what caused", "compare")
- "clarify": Ambiguous or missing context

Respond with JSON: {{"intent": "...", "reasoning": "..."}}"""
    
    response = await llm.ainvoke(prompt)
    
    try:
        result = json.loads(response.content)
        state["intent"] = result.get("intent", "simple")
    except:
        state["intent"] = "simple"  # Default fallback
    
    # Check if clarification needed
    if state["intent"] == "clarify":
        state["needs_clarification"] = True
        state["clarification_question"] = "Could you provide more details about what you're looking for?"
    
    state["step_status"] = "complete"
    return state


def router(state: AgentState) -> Literal["fetch_context", "ask_clarification", "end"]:
    """Route to appropriate path based on intent"""
    
    if state.get("needs_clarification"):
        return "ask_clarification"
    
    return "fetch_context"
