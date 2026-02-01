from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
import json
from app.database import AsyncSessionLocal
from app.models import QuestionHistory, UserProfile
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings

settings = get_settings()


@dataclass
class ContextMessage:
    """A message in the conversation context"""
    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    embedding: Optional[List[float]] = None


class ContextWindowManager:
    """Manages context window for conversations with unlimited history"""
    
    def __init__(
        self,
        max_tokens: int = 4000,
        summary_threshold: int = 10
    ):
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
    
    async def build_context_window(
        self,
        user_id: str,
        tenant_id: str,
        current_query: str,
        recent_messages: int = 5
    ) -> Dict[str, Any]:
        """Build optimized context window for agent"""
        
        async with AsyncSessionLocal() as session:
            # 1. Get recent conversation history
            recent = await self._get_recent_messages(
                session, user_id, tenant_id, limit=recent_messages
            )
            
            # 2. Get semantically similar past queries
            similar = await self._get_similar_queries(
                session, user_id, tenant_id, current_query, limit=3
            )
            
            # 3. Get user profile/preferences
            profile = await self._get_user_profile(session, user_id, tenant_id)
            
            # 4. Summarize older context if needed
            summary = None
            if len(recent) >= self.summary_threshold:
                summary = await self._summarize_conversation(recent[:-recent_messages])
            
            return {
                "recent_messages": recent,
                "similar_past_queries": similar,
                "user_profile": profile,
                "conversation_summary": summary,
                "estimated_tokens": self._estimate_tokens(recent, summary)
            }
    
    async def _get_recent_messages(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get recent conversation messages"""
        query = (
            select(QuestionHistory)
            .where(
                and_(
                    QuestionHistory.user_id == user_id,
                    QuestionHistory.tenant_id == tenant_id
                )
            )
            .order_by(desc(QuestionHistory.created_at))
            .limit(limit)
        )
        
        result = await session.execute(query)
        rows = result.scalars().all()
        
        return [
            {
                "role": "user",
                "content": row.question_text,
                "timestamp": row.created_at.isoformat(),
                "sql": row.generated_sql,
                "result_summary": row.result_summary
            }
            for row in reversed(rows)  # Oldest first
        ]
    
    async def _get_similar_queries(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: str,
        current_query: str,
        limit: int = 3
    ) -> List[Dict]:
        """Get semantically similar past queries using vector search"""
        
        # Generate embedding for current query
        query_embedding = await self.embeddings.aembed_query(current_query)
        
        # Search for similar questions
        # Note: Using pgvector <=> operator for cosine similarity
        sql = """
            SELECT 
                question_text,
                generated_sql,
                result_summary,
                1 - (question_embedding <=> :embedding) as similarity
            FROM question_history
            WHERE user_id = :user_id
            AND tenant_id = :tenant_id
            AND question_embedding IS NOT NULL
            ORDER BY question_embedding <=> :embedding
            LIMIT :limit
        """
        
        result = await session.execute(
            sql,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "embedding": str(query_embedding),
                "limit": limit
            }
        )
        
        rows = result.fetchall()
        
        return [
            {
                "question": row.question_text,
                "sql": row.generated_sql,
                "result": row.result_summary,
                "similarity": row.similarity
            }
            for row in rows if row.similarity > 0.7  # Threshold
        ]
    
    async def _get_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get user preferences and patterns"""
        query = (
            select(UserProfile)
            .where(
                and_(
                    UserProfile.user_id == user_id,
                    UserProfile.tenant_id == tenant_id
                )
            )
        )
        
        result = await session.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            return {}
        
        return {
            "top_topics": profile.top_topics,
            "preferred_metrics": profile.preferred_metrics,
            "preferred_chart_types": profile.preferred_chart_types,
            "active_hours": profile.active_hours,
            "inferred_role": profile.inferred_role
        }
    
    async def _summarize_conversation(
        self,
        messages: List[Dict]
    ) -> str:
        """Summarize older conversation messages"""
        # In production, use LLM to summarize
        # For now, return key topics
        topics = set()
        for msg in messages:
            if msg.get("result_summary"):
                topics.add(msg["result_summary"].get("main_topic", "analysis"))
        
        return f"Previous topics discussed: {', '.join(topics)}" if topics else None
    
    def _estimate_tokens(
        self,
        messages: List[Dict],
        summary: Optional[str]
    ) -> int:
        """Rough token estimation for context window"""
        token_count = 0
        
        for msg in messages:
            token_count += len(msg["content"].split()) * 1.3  # Rough estimate
        
        if summary:
            token_count += len(summary.split()) * 1.3
        
        return int(token_count)
    
    async def add_message(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add a message to conversation history"""
        
        # Generate embedding
        embedding = await self.embeddings.aembed_query(content)
        
        async with AsyncSessionLocal() as session:
            message = QuestionHistory(
                tenant_id=tenant_id,
                user_id=user_id,
                question_text=content if role == "user" else metadata.get("question", ""),
                question_embedding=embedding,
                intent_category=metadata.get("intent"),
                topics=metadata.get("topics", []),
                entities=metadata.get("entities", []),
                generated_sql=metadata.get("sql"),
                result_summary=metadata.get("result"),
                chart_type=metadata.get("chart_type"),
                user_action=metadata.get("action", "viewed"),
                created_at=datetime.utcnow()
            )
            
            session.add(message)
            await session.commit()
            
            return str(message.id)


class ConversationMemory:
    """Long-term conversation memory with summarization"""
    
    def __init__(self):
        self.window_manager = ContextWindowManager()
    
    async def get_relevant_context(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        include_patterns: bool = True
    ) -> Dict[str, Any]:
        """Get all relevant context for a query"""
        
        # Get conversation context
        context = await self.window_manager.build_context_window(
            user_id=user_id,
            tenant_id=tenant_id,
            current_query=query
        )
        
        # Add pattern recognition if enabled
        if include_patterns:
            patterns = await self._detect_patterns(user_id, tenant_id)
            context["detected_patterns"] = patterns
        
        return context
    
    async def _detect_patterns(
        self,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Detect usage patterns from history"""
        
        async with AsyncSessionLocal() as session:
            # Get last 30 days of queries
            from datetime import timedelta
            
            query = (
                select(QuestionHistory)
                .where(
                    and_(
                        QuestionHistory.user_id == user_id,
                        QuestionHistory.tenant_id == tenant_id,
                        QuestionHistory.created_at >= datetime.utcnow() - timedelta(days=30)
                    )
                )
            )
            
            result = await session.execute(query)
            history = result.scalars().all()
            
            if not history:
                return {}
            
            # Analyze patterns
            topics = {}
            times = {}
            
            for h in history:
                # Topic frequency
                if h.topics:
                    for topic in h.topics:
                        topics[topic] = topics.get(topic, 0) + 1
                
                # Time patterns
                hour = h.created_at.hour
                times[hour] = times.get(hour, 0) + 1
            
            # Find most active hours
            peak_hours = sorted(times.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                "top_topics": sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5],
                "peak_hours": [h[0] for h in peak_hours],
                "total_queries": len(history),
                "avg_queries_per_day": len(history) / 30
            }
    
    async def search_memory(
        self,
        user_id: str,
        tenant_id: str,
        search_query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Semantic search through conversation memory"""
        
        embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
        
        query_embedding = await embeddings.aembed_query(search_query)
        
        async with AsyncSessionLocal() as session:
            sql = """
                SELECT 
                    question_text,
                    generated_sql,
                    result_summary,
                    created_at,
                    1 - (question_embedding <=> :embedding) as similarity
                FROM question_history
                WHERE user_id = :user_id
                AND tenant_id = :tenant_id
                AND question_embedding IS NOT NULL
                ORDER BY question_embedding <=> :embedding
                LIMIT :limit
            """
            
            result = await session.execute(
                sql,
                {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "embedding": str(query_embedding),
                    "limit": limit
                }
            )
            
            rows = result.fetchall()
            
            return [
                {
                    "question": row.question_text,
                    "sql": row.generated_sql,
                    "result": row.result_summary,
                    "timestamp": row.created_at.isoformat(),
                    "relevance": row.similarity
                }
                for row in rows
            ]
