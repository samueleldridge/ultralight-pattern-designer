"""
User-friendly step messages for the agent workflow.
Maps technical step names to human-readable descriptions.
"""

from typing import Dict, Optional

STEP_MESSAGES = {
    # Workflow steps
    "classify_intent": {
        "started": "Understanding your question...",
        "in_progress": "Figuring out what you're looking for...",
        "complete": "Got it — analyzing your request"
    },
    "fetch_context": {
        "started": "Gathering relevant information...",
        "in_progress": "Looking up your data structure...",
        "complete": "Found the relevant data"
    },
    "generate_sql": {
        "started": "Formulating the query...",
        "in_progress": "Writing the database query...",
        "complete": "Query ready"
    },
    "validate_sql": {
        "started": "Double-checking the query...",
        "in_progress": "Validating for safety...",
        "complete": "Query validated"
    },
    "execute_sql": {
        "started": "Running the query...",
        "in_progress": "Fetching your data...",
        "complete": "Data retrieved"
    },
    "analyze_error": {
        "started": "Looking into the issue...",
        "in_progress": "Figuring out what went wrong...",
        "complete": "Found a solution"
    },
    "analyze_results": {
        "started": "Analyzing the results...",
        "in_progress": "Finding patterns in your data...",
        "complete": "Analysis complete"
    },
    "generate_viz": {
        "started": "Creating your visualization...",
        "in_progress": "Building the chart...",
        "complete": "Chart ready"
    },
    "ask_clarification": {
        "started": "Need a bit more info...",
        "in_progress": "Clarifying your question...",
        "complete": "Waiting for clarification"
    },
    "end": {
        "started": "Wrapping up...",
        "in_progress": "Finalizing...",
        "complete": "Done!"
    }
}

STEP_ICONS = {
    "classify_intent": "💭",
    "fetch_context": "🔍",
    "generate_sql": "⚡",
    "validate_sql": "✓",
    "execute_sql": "📊",
    "analyze_error": "🔧",
    "analyze_results": "📈",
    "generate_viz": "📉",
    "ask_clarification": "❓",
    "end": "✅"
}

STEP_ORDER = [
    "classify_intent",
    "fetch_context", 
    "generate_sql",
    "validate_sql",
    "execute_sql",
    "analyze_results",
    "generate_viz",
    "end"
]


def get_user_friendly_message(step: str, status: str) -> str:
    """Get human-readable message for a step"""
    step_info = STEP_MESSAGES.get(step, {})
    return step_info.get(status, f"{step.replace('_', ' ').title()}...")


def get_step_icon(step: str) -> str:
    """Get icon for step"""
    return STEP_ICONS.get(step, "•")


def calculate_progress(step: str) -> int:
    """Calculate progress percentage based on current step"""
    if step not in STEP_ORDER:
        return 0
    
    index = STEP_ORDER.index(step)
    return int((index / len(STEP_ORDER)) * 100)


def get_step_category(step: str) -> str:
    """Categorize step for UI styling"""
    thinking_steps = ["classify_intent", "fetch_context", "analyze_results"]
    action_steps = ["generate_sql", "execute_sql", "generate_viz"]
    check_steps = ["validate_sql"]
    error_steps = ["analyze_error", "ask_clarification"]
    
    if step in thinking_steps:
        return "thinking"
    elif step in action_steps:
        return "action"
    elif step in check_steps:
        return "check"
    elif step in error_steps:
        return "error"
    else:
        return "default"
