"""
Enhanced Intent Classification Node

Uses the advanced NLP intent classification with:
- Few-shot prompting
- Ambiguity detection
- Follow-up detection
- Clarification generation
"""

import json
from typing import Literal
from app.llm_provider import get_llm_provider
from app.config import get_settings
from app.agent.state import AgentState
from app.nlp.intent_classification import classify_intent, IntentType
from app.nlp.context_management import get_session_manager

settings = get_settings()
llm_provider = get_llm_provider()


async def classify_intent_node(state: AgentState) -> AgentState:
    """
    Enhanced intent classification with ambiguity detection and follow-up handling.
    """
    
    state["current_step"] = "classify_intent"
    state["step_message"] = "Understanding your question..."
    state["step_status"] = "in_progress"
    
    try:
        # Get conversation context if available
        session_manager = get_session_manager()
        session = session_manager.get_or_create_session(
            session_id=state.get("workflow_id", "default"),
            user_id=state["user_id"],
            tenant_id=state["tenant_id"]
        )
        
        # Get recent conversation history
        recent_contexts = session.get_recent(3)
        conversation_history = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": ctx.query,
                "intent": ctx.intent
            }
            for i, ctx in enumerate(recent_contexts)
        ]
        
        # Classify intent with full context
        classification = await classify_intent(
            query=state["query"],
            conversation_history=conversation_history,
            user_profile=state.get("user_context")
        )
        
        # Store classification results
        state["intent"] = classification.intent.value
        state["intent_confidence"] = classification.confidence
        state["intent_reasoning"] = classification.reasoning
        state["ambiguity_level"] = classification.ambiguity_level.value
        state["referenced_entities"] = classification.referenced_entities
        state["is_follow_up"] = classification.is_follow_up
        
        # Handle follow-up queries
        if classification.is_follow_up and recent_contexts:
            # Resolve the contextual reference
            from app.nlp.context_management import ContextResolver
            resolver = ContextResolver()
            
            resolved_query, resolution_metadata = await resolver.resolve(
                state["query"], session
            )
            
            if resolution_metadata.get("resolved"):
                state["resolved_query"] = resolved_query
                state["resolution_metadata"] = resolution_metadata
                state["step_message"] = "Understanding follow-up question..."
        
        # Check if clarification is needed
        if classification.needs_clarification():
            state["needs_clarification"] = True
            
            # Generate clarification question
            clarification = await classification.generate_clarification_question(
                state["query"]
            )
            
            state["clarification_question"] = clarification.get(
                "clarification_question",
                "Could you provide more details about what you're looking for?"
            )
            state["clarification_options"] = clarification.get("options", [])
            state["suggested_queries"] = clarification.get("suggested_queries", [])
            
            # Store ambiguities for later reference
            state["ambiguities"] = [
                {
                    "type": a.type,
                    "description": a.description,
                    "possible_interpretations": a.possible_interpretations
                }
                for a in classification.ambiguities
            ]
        else:
            state["needs_clarification"] = False
        
        state["step_status"] = "complete"
        
    except Exception as e:
        # Fallback to simple classification on error
        state["intent"] = "simple"
        state["intent_confidence"] = 0.5
        state["needs_clarification"] = False
        state["step_status"] = "complete"
        state["error"] = f"Intent classification warning: {str(e)}"
    
    return state


def router(state: AgentState) -> Literal["fetch_context", "ask_clarification", "end"]:
    """Route to appropriate path based on intent"""
    
    if state.get("needs_clarification"):
        return "ask_clarification"
    
    # Handle greetings and meta queries
    if state.get("intent") == "greeting":
        state["clarification_question"] = "Hello! I'm your AI analytics assistant. What would you like to know about your data?"
        state["needs_clarification"] = True
        return "ask_clarification"
    
    if state.get("intent") == "meta":
        state["clarification_question"] = "I can help you analyze your data. Try asking questions like 'What was revenue last month?' or 'Show me top products by sales.'"
        state["needs_clarification"] = True
        return "ask_clarification"
    
    return "fetch_context"
