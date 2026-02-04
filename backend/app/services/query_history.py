"""
Query History Service

Tracks user queries with embeddings for semantic search.
Enables "Recent Queries" sidebar and similar query suggestions.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from app.database import AsyncSessionLocal
from app.models import QuestionHistory
from sqlalchemy import select, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class QueryRecord:
    """A recorded query with metadata"""
    id: str
    query: str
    sql: Optional[str]
    result_summary: Optional[str]
    embedding: Optional[List[float]]  # Vector embedding for semantic search
    user_id: str
    tenant_id: str
    created_at: datetime
    execution_time_ms: Optional[int]
    success: bool
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class QueryHistoryService:
    """Service for managing query history with semantic search"""
    
    def __init__(self):
        self.embedding_model = None  # Lazy load
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified - uses hash-based for now)"""
        # In production, use OpenAI embeddings or local model
        # For MVP, create a simple hash-based vector
        hash_obj = hashlib.sha256(text.lower().encode())
        # Create 10-dimensional vector from hash
        hash_bytes = hash_obj.digest()
        return [float((hash_bytes[i] + hash_bytes[i+10]) % 100) / 100 for i in range(10)]
    
    async def record_query(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        sql: Optional[str] = None,
        result_summary: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True
    ) -> QueryRecord:
        """Record a new query in history"""
        
        async with AsyncSessionLocal() as session:
            # Generate embedding
            embedding = await self._get_embedding(query)
            
            # Create record
            record = QuestionHistory(
                id=self._generate_id(),
                user_id=user_id,
                tenant_id=tenant_id,
                question=query,
                sql_generated=sql,
                results_summary=result_summary,
                created_at=datetime.utcnow(),
                execution_time_ms=execution_time_ms
            )
            
            session.add(record)
            await session.commit()
            
            return QueryRecord(
                id=record.id,
                query=query,
                sql=sql,
                result_summary=result_summary,
                embedding=embedding,
                user_id=user_id,
                tenant_id=tenant_id,
                created_at=record.created_at,
                execution_time_ms=execution_time_ms,
                success=success
            )
    
    async def get_recent_queries(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 10,
        days: int = 30
    ) -> List[QueryRecord]:
        """Get recent queries for a user"""
        
        async with AsyncSessionLocal() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(QuestionHistory)
                .where(
                    QuestionHistory.user_id == user_id,
                    QuestionHistory.tenant_id == tenant_id,
                    QuestionHistory.created_at >= cutoff
                )
                .order_by(desc(QuestionHistory.created_at))
                .limit(limit)
            )
            
            rows = result.scalars().all()
            
            return [
                QueryRecord(
                    id=row.id,
                    query=row.question,
                    sql=row.sql_generated,
                    result_summary=row.results_summary,
                    embedding=None,  # Don't return embeddings
                    user_id=row.user_id,
                    tenant_id=row.tenant_id,
                    created_at=row.created_at,
                    execution_time_ms=row.execution_time_ms,
                    success=True
                )
                for row in rows
            ]
    
    async def search_similar_queries(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        limit: int = 5
    ) -> List[QueryRecord]:
        """Find semantically similar past queries"""
        
        # Get embedding for search query
        query_embedding = await self._get_embedding(query)
        
        # Get recent queries
        recent = await self.get_recent_queries(user_id, tenant_id, limit=50)
        
        # Calculate similarity scores (cosine similarity)
        scored = []
        for record in recent:
            if record.embedding:
                similarity = self._cosine_similarity(query_embedding, record.embedding)
                scored.append((record, similarity))
        
        # Sort by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top matches (above threshold)
        threshold = 0.7
        return [record for record, score in scored[:limit] if score > threshold]
    
    async def get_popular_queries(
        self,
        tenant_id: str,
        limit: int = 10,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get most popular queries in a tenant"""
        
        async with AsyncSessionLocal() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(
                    QuestionHistory.question,
                    func.count(QuestionHistory.id).label('count')
                )
                .where(
                    QuestionHistory.tenant_id == tenant_id,
                    QuestionHistory.created_at >= cutoff
                )
                .group_by(QuestionHistory.question)
                .order_by(desc('count'))
                .limit(limit)
            )
            
            return [
                {"query": row[0], "count": row[1]}
                for row in result.fetchall()
            ]
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)


# Singleton instance
_query_history_service: Optional[QueryHistoryService] = None


def get_query_history_service() -> QueryHistoryService:
    """Get or create query history service"""
    global _query_history_service
    if _query_history_service is None:
        _query_history_service = QueryHistoryService()
    return _query_history_service
