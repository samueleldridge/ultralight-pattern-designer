import json
from app.llm_provider import get_llm_provider
from app.agent.state import AgentState

# Get the unified LLM provider (Kimi K2.5 primary, OpenAI fallback)
llm_provider = get_llm_provider()


async def generate_sql_node(state: AgentState) -> AgentState:
    """Generate SQL from natural language using Kimi K2.5"""
    
    state["current_step"] = "generate_sql"
    state["step_message"] = "Generating SQL query with Kimi K2.5..."
    state["step_status"] = "in_progress"
    
    # Build context-rich prompt
    context_parts = []
    
    if state.get("schema_context"):
        tables = state["schema_context"].get("tables", [])
        context_parts.append(f"Available tables: {json.dumps(tables, indent=2)}")
    
    if state.get("few_shot_examples"):
        examples = state["few_shot_examples"]
        context_parts.append(f"Similar past queries:\n{json.dumps(examples, indent=2)}")
    
    if state.get("semantic_definitions"):
        definitions = state["semantic_definitions"]
        context_parts.append(f"Business definitions:\n{json.dumps(definitions, indent=2)}")
    
    if state.get("user_context"):
        user_ctx = state["user_context"]
        context_parts.append(f"User preferences: {json.dumps(user_ctx)}")
    
    context_str = "\n\n".join(context_parts)
    
    # System prompt optimized for Kimi K2.5
    system_prompt = """You are an expert SQL analyst powered by Kimi K2.5. 
Your task is to generate accurate, optimized PostgreSQL queries from natural language questions.

Guidelines:
1. Generate valid PostgreSQL syntax
2. Use ONLY tables and columns provided in the context
3. Optimize for performance (use appropriate indexes, avoid SELECT *)
4. Include clear, descriptive column aliases
5. Handle edge cases (nulls, type casting, date ranges)
6. Return ONLY valid JSON in the specified format"""

    prompt = f"""Generate a PostgreSQL query for the following question.

Context:
{context_str}

Question: "{state['query']}"

Requirements:
- Answer the question accurately
- Use only available tables/columns
- Optimize the query (use appropriate joins, filters)
- Include clear column aliases

Respond with this exact JSON structure:
{{
    "sql": "SELECT ...",
    "explanation": "Brief explanation of what this query does",
    "chart_type": "line|bar|table|pie|metric",
    "confidence": 0.0-1.0
}}"""

    try:
        # Use Kimi K2.5 via the LLM provider
        result = await llm_provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        state["sql"] = result.get("sql", "").strip()
        state["visualization_config"] = {
            "type": result.get("chart_type", "table"),
            "explanation": result.get("explanation", "")
        }
        state["confidence"] = result.get("confidence", 0.8)
        
        if not state["sql"]:
            raise ValueError("Generated SQL is empty")
            
    except Exception as e:
        # Handle errors gracefully
        state["sql"] = "-- Failed to generate SQL"
        state["error"] = str(e)
        state["step_status"] = "error"
        state["step_message"] = f"SQL generation failed: {str(e)}"
        return state
    
    state["step_status"] = "complete"
    state["step_message"] = "SQL generated successfully"
    return state


async def generate_sql_node_v2(state: AgentState) -> AgentState:
    """
    Enhanced SQL generation with multi-turn reasoning and validation.
    Uses Kimi K2.5's advanced reasoning capabilities.
    """
    
    state["current_step"] = "generate_sql_v2"
    state["step_message"] = "Analyzing with Kimi K2.5 enhanced reasoning..."
    state["step_status"] = "in_progress"
    
    # Step 1: Analyze the question
    analysis_prompt = f"""Analyze this analytics question and identify:
1. Key entities (tables, columns needed)
2. Time dimensions (if any)
3. Aggregation requirements
4. Filter conditions
5. Potential edge cases

Question: "{state['query']}"

Available context: {json.dumps(state.get('schema_context', {}), indent=2)}

Respond with JSON:
{{
    "entities": ["table.column"],
    "time_range": "description or null",
    "aggregations": ["SUM", "AVG", etc],
    "filters": ["condition1", "condition2"],
    "edge_cases": ["description1"]
}}"""

    try:
        # Analyze the query first
        analysis = await llm_provider.generate_json(
            prompt=analysis_prompt,
            system_prompt="You are a data analyst. Break down the question into components.",
            temperature=0.1
        )
        
        state["analysis"] = analysis
        
        # Step 2: Generate SQL with the analysis
        sql_prompt = f"""Generate PostgreSQL query based on this analysis:

Analysis: {json.dumps(analysis, indent=2)}

Original question: "{state['query']}"

Schema context: {json.dumps(state.get('schema_context', {}), indent=2)}

Semantic definitions: {json.dumps(state.get('semantic_definitions', []), indent=2)}

Generate optimized SQL. Respond with JSON:
{{
    "sql": "SELECT ...",
    "explanation": "...",
    "chart_type": "line|bar|table|pie|metric",
    "parameters": ["param1"],
    "estimated_rows": 1000
}}"""

        result = await llm_provider.generate_json(
            prompt=sql_prompt,
            system_prompt="You are a PostgreSQL expert. Generate optimal, secure queries.",
            temperature=0.1
        )
        
        state["sql"] = result.get("sql", "").strip()
        state["visualization_config"] = {
            "type": result.get("chart_type", "table"),
            "explanation": result.get("explanation", ""),
            "parameters": result.get("parameters", [])
        }
        
    except Exception as e:
        state["sql"] = "-- Generation failed"
        state["error"] = str(e)
        state["step_status"] = "error"
        return state
    
    state["step_status"] = "complete"
    return state
