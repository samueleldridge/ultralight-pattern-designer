from typing import Dict, List, Optional, Any
import json
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.agent.state import AgentState
from app.database.connector import DatabaseConfig, DatabaseConnector, SchemaTable
from app.database.dialect import SQLDialect, SQLDialectAdapter

settings = get_settings()
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.1,
    api_key=settings.openai_api_key
)


async def generate_sql_node(state: AgentState) -> AgentState:
    """Generate SQL from natural language with dialect awareness"""
    
    state["current_step"] = "generate_sql"
    state["step_message"] = "Generating SQL query..."
    state["step_status"] = "in_progress"
    
    # Get dialect hints
    dialect = state.get("dialect", "postgresql")
    dialect_hints = SQLDialectAdapter.get_dialect_specific_prompt_hints(SQLDialect(dialect))
    
    # Build context
    context_parts = []
    
    # Schema context
    if state.get("schema_context"):
        tables = state["schema_context"].get("tables", [])
        context_parts.append("Available Tables:")
        for table in tables:
            table_desc = f"\n- {table['name']}"
            if table.get('columns'):
                cols = ', '.join([c['name'] for c in table['columns'][:10]])
                table_desc += f" ({cols}{'...' if len(table['columns']) > 10 else ''})"
            context_parts.append(table_desc)
    
    # Few-shot examples
    if state.get("few_shot_examples"):
        context_parts.append("\nSimilar Past Queries:")
        for ex in state["few_shot_examples"][:2]:
            context_parts.append(f"Q: {ex['question']}")
            context_parts.append(f"SQL: {ex['sql'][:100]}...")
    
    # Semantic definitions
    if state.get("semantic_definitions"):
        context_parts.append("\nBusiness Definitions:")
        for concept, defn in state["semantic_definitions"].items():
            context_parts.append(f"- {concept}: {defn.get('definition', '')}")
    
    context_str = "\n".join(context_parts)
    
    prompt = f"""You are an expert SQL analyst. Generate a {dialect} SQL query for the following question.

{dialect_hints}

{context_str}

User Question: "{state['query']}"

Requirements:
1. Generate syntactically correct {dialect} SQL
2. Use only tables/columns from the schema above
3. Add appropriate WHERE clauses to limit results
4. Include ORDER BY if relevant
5. Use LIMIT to prevent returning too many rows

Respond with JSON:
{{
    "sql": "SELECT ...",
    "explanation": "What this query does",
    "chart_type": "line|bar|table|pie|metric",
    "x_column": "column for x-axis (if chart)",
    "y_column": "column for y-axis (if chart)",
    "time_column": "column containing dates (if time series)"
}}"""
    
    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)
        
        state["sql"] = result.get("sql", "")
        state["visualization_config"] = {
            "type": result.get("chart_type", "table"),
            "x_axis": result.get("x_column"),
            "y_axis": result.get("y_column"),
            "time_column": result.get("time_column"),
            "explanation": result.get("explanation", "")
        }
        state["step_status"] = "complete"
        
    except json.JSONDecodeError:
        # Try to extract SQL from response
        content = response.content
        if "SELECT" in content.upper():
            # Extract SQL between code blocks or quotes
            import re
            sql_match = re.search(r'```sql\s*(.*?)```', content, re.DOTALL)
            if sql_match:
                state["sql"] = sql_match.group(1).strip()
            else:
                # Just take everything after SELECT
                select_idx = content.upper().find("SELECT")
                state["sql"] = content[select_idx:].split('\n')[0].strip()
            
            state["visualization_config"] = {"type": "table"}
            state["step_status"] = "complete"
        else:
            state["sql"] = "-- Failed to generate SQL"
            state["step_status"] = "error"
    
    except Exception as e:
        state["sql"] = f"-- Error: {str(e)}"
        state["step_status"] = "error"
    
    return state
