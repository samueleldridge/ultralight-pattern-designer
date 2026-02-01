import asyncio
from typing import Dict, List, Optional
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select, text
from app.agent.state import AgentState
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import QuestionHistory

settings = get_settings()
embeddings = OpenAIEmbeddings(
    model=settings.openai_embedding_model,
    api_key=settings.openai_api_key or "sk-test"
)


async def fetch_context_node(state: AgentState) -> AgentState:
    """Fetch all relevant context in parallel"""
    
    state["current_step"] = "fetch_context"
    state["step_message"] = "Loading relevant context..."
    state["step_status"] = "in_progress"
    
    # Run all fetches in parallel
    results = await asyncio.gather(
        fetch_user_profile(state["user_id"]),
        fetch_schema_context(state.get("connection_id")),
        fetch_few_shot_examples(state["query"], state["user_id"]),
        fetch_semantic_definitions(state["tenant_id"]),
        return_exceptions=True
    )
    
    state["user_context"] = results[0] if not isinstance(results[0], Exception) else {}
    state["schema_context"] = results[1] if not isinstance(results[1], Exception) else {}
    state["few_shot_examples"] = results[2] if not isinstance(results[2], Exception) else []
    state["semantic_definitions"] = results[3] if not isinstance(results[3], Exception) else {}
    
    state["step_status"] = "complete"
    return state


async def fetch_user_profile(user_id: str) -> Dict:
    """Fetch user preferences and patterns"""
    # TODO: Implement DB query
    return {
        "top_topics": ["revenue", "sales"],
        "preferred_metrics": ["total_revenue", "active_users"],
        "preferred_chart_types": ["line", "bar"]
    }


async def fetch_schema_context(connection_id: Optional[str]) -> Dict:
    """Fetch relevant schema from cache"""
    # TODO: Implement schema introspection
    return {
        "tables": [
            {
                "name": "orders",
                "columns": ["id", "total", "created_at", "user_id"],
                "description": "Customer orders"
            },
            {
                "name": "users",
                "columns": ["id", "email", "created_at"],
                "description": "User accounts"
            }
        ]
    }


async def fetch_few_shot_examples(query: str, user_id: str) -> List[Dict]:
    """Fetch similar past queries using vector search"""
    
    try:
        # Generate embedding for current query
        query_embedding = await embeddings.aembed_query(query)
        
        # Search similar questions
        async with AsyncSessionLocal() as session:
            # Using pgvector cosine similarity
            sql = text("""
                SELECT question_text, generated_sql, result_summary
                FROM question_history
                WHERE user_id = :user_id
                ORDER BY question_embedding <=> :embedding
                LIMIT 3
            """)
            result = await session.execute(
                sql,
                {"user_id": user_id, "embedding": str(query_embedding)}
            )
            rows = result.fetchall()
            
            return [
                {
                    "question": row.question_text,
                    "sql": row.generated_sql,
                    "result": row.result_summary
                }
                for row in rows
            ]
    except Exception as e:
        print(f"Error fetching few-shot examples: {e}")
        return []


async def fetch_semantic_definitions(tenant_id: str) -> Dict:
    """Fetch business terms and definitions"""
    # TODO: Implement semantic layer
    return {
        "revenue": {
            "definition": "Total order value after discounts",
            "calculation": "SUM(orders.total - orders.discount)"
        }
    }
