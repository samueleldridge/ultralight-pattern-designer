"""
Enhanced SQL Generation Node

Features:
- Few-shot prompting with examples
- Schema-aware prompting
- Query optimization hints
- Multi-turn conversation support
- Entity extraction integration
"""

import json
from typing import Dict, List, Optional, Any
from app.llm_provider import get_llm_provider
from app.agent.state import AgentState
from app.prompts.registry import get_prompt, PromptType
from app.nlp.entity_extraction import extract_entities, DateParser
from app.nlp.context_management import get_session_manager

llm_provider = get_llm_provider()


async def generate_sql_node_enhanced(state: AgentState) -> AgentState:
    """
    Enhanced SQL generation with schema awareness, few-shot examples,
    and entity extraction.
    """
    
    state["current_step"] = "generate_sql"
    state["step_message"] = "Generating optimized SQL query..."
    state["step_status"] = "in_progress"
    
    try:
        # Use resolved query if this was a follow-up
        query_to_process = state.get("resolved_query", state["query"])
        
        # Extract entities from query
        schema_context = state.get("schema_context", {})
        entities = await extract_entities(query_to_process, schema_context)
        state["extracted_entities"] = entities.to_dict()
        
        # Build rich context for prompt
        context_str = _build_schema_context(schema_context)
        few_shot_str = _build_few_shot_examples(state.get("few_shot_examples", []))
        semantic_str = _build_semantic_definitions(state.get("semantic_definitions", {}))
        
        # Get conversation history
        conversation_history = await _build_conversation_history(state)
        
        # Get dialect hints
        dialect = state.get("dialect", "postgresql")
        
        # Use enhanced prompt template
        prompt_template = get_prompt("sql_generator", PromptType.SQL_GENERATION, version="2.0")
        
        prompt = prompt_template.render(
            dialect=dialect,
            schema_context=context_str,
            few_shot_examples=few_shot_str,
            semantic_definitions=semantic_str,
            conversation_history=conversation_history,
            query=query_to_process,
            extracted_entities=json.dumps(entities.to_dict(), indent=2, default=str),
            user_preferences=json.dumps(state.get("user_context", {}))
        )
        
        # Generate SQL with enhanced prompting
        result = await llm_provider.generate_json(
            prompt=prompt,
            system_prompt="""You are an expert SQL analyst. Generate accurate, optimized PostgreSQL queries.
Follow these principles:
1. Use CTEs for complex logic
2. Always include explicit time filters
3. Use proper JOIN syntax
4. Add comments for complex calculations
5. Include row limits
6. Optimize for readability""",
            temperature=0.1
        )
        
        # Extract SQL and metadata
        sql = result.get("sql", "").strip()
        
        if not sql:
            raise ValueError("Generated SQL is empty")
        
        state["sql"] = sql
        state["sql_analysis"] = result.get("analysis", {})
        
        # Store visualization config
        state["visualization_config"] = {
            "type": result.get("chart_type", "table"),
            "explanation": result.get("explanation", ""),
            "columns": result.get("columns", {}),
            "parameters": result.get("parameters", [])
        }
        
        state["confidence"] = result.get("confidence", 0.8)
        state["optimization_notes"] = result.get("performance_notes", [])
        state["sql_generation_assumptions"] = result.get("assumptions_made", [])
        
        state["step_status"] = "complete"
        state["step_message"] = "SQL generated successfully"
        
    except Exception as e:
        state["sql"] = f"-- Generation failed: {str(e)}"
        state["error"] = str(e)
        state["step_status"] = "error"
        state["step_message"] = f"SQL generation error: {str(e)}"
    
    return state


def _build_schema_context(schema_context: Dict) -> str:
    """Build detailed schema context string"""
    
    if not schema_context:
        return "No schema context available"
    
    parts = []
    tables = schema_context.get("tables", [])
    
    for table in tables:
        table_name = table.get("name", "unknown")
        description = table.get("description", "")
        
        table_str = f"\nTable: {table_name}"
        if description:
            table_str += f" - {description}"
        
        # Add columns
        columns = table.get("columns", [])
        if columns:
            table_str += "\n  Columns:"
            for col in columns:
                if isinstance(col, dict):
                    col_name = col.get("name", "unknown")
                    col_type = col.get("type", "unknown")
                    col_desc = col.get("description", "")
                    table_str += f"\n    - {col_name} ({col_type})"
                    if col_desc:
                        table_str += f": {col_desc}"
                else:
                    table_str += f"\n    - {col}"
        
        # Add relationships
        relationships = table.get("relationships", [])
        if relationships:
            table_str += "\n  Relationships:"
            for rel in relationships:
                table_str += f"\n    - {rel}"
        
        parts.append(table_str)
    
    return "\n".join(parts)


def _build_few_shot_examples(examples: List[Dict]) -> str:
    """Build few-shot examples string"""
    
    if not examples:
        return "No similar past queries"
    
    parts = []
    for i, ex in enumerate(examples[:3], 1):
        parts.append(f"\nExample {i}:")
        parts.append(f"  Question: {ex.get('question', 'N/A')}")
        parts.append(f"  SQL: {ex.get('sql', 'N/A')[:150]}...")
        if ex.get('result'):
            parts.append(f"  Result: {ex.get('result')}")
    
    return "\n".join(parts)


def _build_semantic_definitions(definitions: Dict) -> str:
    """Build semantic definitions string"""
    
    if not definitions:
        return "No business definitions available"
    
    parts = []
    for concept, defn in definitions.items():
        if isinstance(defn, dict):
            definition = defn.get("definition", "")
            calculation = defn.get("calculation", "")
            parts.append(f"\n{concept}:")
            if definition:
                parts.append(f"  Definition: {definition}")
            if calculation:
                parts.append(f"  Calculation: {calculation}")
        else:
            parts.append(f"\n{concept}: {defn}")
    
    return "\n".join(parts)


async def _build_conversation_history(state: AgentState) -> str:
    """Build conversation history string"""
    
    session_manager = get_session_manager()
    session = session_manager.get_or_create_session(
        session_id=state.get("workflow_id", "default"),
        user_id=state["user_id"],
        tenant_id=state["tenant_id"]
    )
    
    recent = session.get_recent(3)
    if not recent:
        return "No previous conversation"
    
    parts = ["Recent conversation:"]
    for ctx in recent:
        parts.append(f"\nUser: {ctx.query}")
        if ctx.sql:
            parts.append(f"SQL: {ctx.sql[:100]}...")
        if ctx.results_summary:
            parts.append(f"Result: {ctx.results_summary}")
    
    return "\n".join(parts)


async def generate_sql_with_retry(state: AgentState, max_retries: int = 2) -> AgentState:
    """
    Generate SQL with automatic retry on validation failure.
    """
    
    for attempt in range(max_retries + 1):
        state = await generate_sql_node_enhanced(state)
        
        if state.get("step_status") != "error":
            break
        
        if attempt < max_retries:
            state["step_message"] = f"Retrying SQL generation (attempt {attempt + 2}/{max_retries + 1})..."
            # Add error context for next attempt
            state["previous_error"] = state.get("error")
    
    return state
