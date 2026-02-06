"""
User Memory & Proactive Intelligence System

Architecture:
- UserProfile: Long-term memory store (interests, patterns, preferences)
- UserInteraction: Complete LLM conversation history
- InterestDetection: NLP-based theme extraction from queries
- MemoryConsolidation: Periodic memory updates based on interactions
- ProactiveIntelligence: Discovery engine for new insights

Flow:
1. User query → Store interaction + extract themes
2. Daily/weekly consolidation → Update user memory profile  
3. Proactive cron → Analyze patterns → Discover new data → Generate suggestions
4. Deliver suggestions via notification API
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from sqlalchemy import select, desc, func, and_, text, Column, String, DateTime, Text, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base, AsyncSessionLocal
from app.models import QuestionHistory


class InterestCategory(str, Enum):
    """Categories of user interests"""
    METRICS = "metrics"  # KPIs, totals, averages
    TRENDS = "trends"    # Time-series, changes over time
    COMPARISONS = "comparisons"  # vs analysis, benchmarks
    SEGMENTS = "segments"  # breakdowns, groupings
    ANOMALIES = "anomalies"  # outliers, unexpected patterns
    PREDICTIONS = "predictions"  # forecasts, projections


class ProactivePriority(str, Enum):
    """Priority levels for proactive suggestions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class UserInterest:
    """A detected user interest with metadata"""
    topic: str  # e.g., "revenue", "customer churn"
    category: InterestCategory
    frequency: int  # How often asked
    last_asked: datetime
    confidence: float  # 0-1
    related_entities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "category": self.category.value,
            "frequency": self.frequency,
            "last_asked": self.last_asked.isoformat(),
            "confidence": self.confidence,
            "related_entities": self.related_entities
        }


@dataclass  
class ProactiveSuggestion:
    """A suggestion generated proactively for the user"""
    id: str
    user_id: str
    tenant_id: str
    title: str
    description: str
    suggested_query: str
    reason: str  # Why this is relevant
    source_themes: List[str]
    new_data_evidence: Dict
    priority: ProactivePriority
    created_at: datetime
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "suggested_query": self.suggested_query,
            "reason": self.reason,
            "source_themes": self.source_themes,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat()
        }


class UserProfile(Base):
    """Long-term user memory and preferences"""
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),
        {'extend_existing': True}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    
    # Long-term memory
    interests = Column(JSONB, default=list)  # List of UserInterest dicts
    preferred_chart_types = Column(JSONB, default=list)  # ['line', 'bar', 'metric']
    common_filters = Column(JSONB, default=dict)  # {entity: [values]}
    
    # Memory summary (natural language)
    memory_summary = Column(Text, default="")
    
    # Usage patterns
    peak_usage_hours = Column(JSONB, default=list)  # [9, 10, 14, 15]
    typical_query_complexity = Column(String, default="medium")  # simple/medium/complex
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_proactive_check = Column(DateTime, nullable=True)


class UserInteraction(Base):
    """Complete record of user-LLM interactions"""
    __tablename__ = "user_interactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True)
    
    # Query details
    query = Column(Text, nullable=False)
    normalized_query = Column(Text, index=True)  # Lowercase, stemmed for matching
    
    # Response details
    sql_generated = Column(Text)
    response_summary = Column(Text)
    chart_type = Column(String)
    
    # Extracted intelligence
    themes = Column(JSONB, default=list)  # Extracted topics
    entities_mentioned = Column(JSONB, default=list)  # LBG, Product X, etc.
    intent = Column(String)  # explore, compare, monitor, alert
    
    # Metrics
    execution_time_ms = Column(Integer)
    row_count = Column(Integer)
    
    # Proactive tracking
    led_to_followup = Column(Boolean, default=False)  # Did user ask follow-up?
    added_to_dashboard = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProactiveSuggestionRecord(Base):
    """Stored proactive suggestions for delivery"""
    __tablename__ = "proactive_suggestions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    
    suggestion_data = Column(JSONB, nullable=False)
    
    # Delivery tracking
    priority = Column(String, default="medium")
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime)
    delivery_channel = Column(String)  # email, slack, in_app
    
    # User feedback
    viewed = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class InterestDetectionService:
    """Extract themes and interests from user queries"""
    
    # Keywords that indicate interest categories
    CATEGORY_PATTERNS = {
        InterestCategory.METRICS: ['total', 'sum', 'average', 'mean', 'count', 'how many', 'how much'],
        InterestCategory.TRENDS: ['trend', 'over time', 'month over month', 'growth', 'change', 'increase', 'decrease'],
        InterestCategory.COMPARISONS: ['compare', 'versus', 'vs', 'difference', 'better', 'worse', 'benchmark'],
        InterestCategory.SEGMENTS: ['by', 'breakdown', 'group', 'segment', 'split', 'per', 'each'],
        InterestCategory.ANOMALIES: ['anomaly', 'outlier', 'unusual', 'strange', 'unexpected', 'spike', 'drop'],
        InterestCategory.PREDICTIONS: ['forecast', 'predict', 'projection', 'will', 'next month', 'future']
    }
    
    # Common business entities to track
    ENTITY_PATTERNS = {
        'revenue': ['revenue', 'sales', 'income', 'turnover'],
        'customers': ['customer', 'client', 'user', 'account'],
        'products': ['product', 'item', 'sku', 'offering'],
        'orders': ['order', 'purchase', 'transaction', 'sale'],
        'churn': ['churn', 'retention', 'cancel', 'leave'],
        'growth': ['growth', 'expansion', 'increase', 'scaling']
    }
    
    def detect_themes(self, query: str) -> List[Dict]:
        """Extract themes from a query"""
        query_lower = query.lower()
        themes = []
        
        # Detect categories
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    themes.append({
                        "type": "category",
                        "value": category.value,
                        "confidence": 0.8 if pattern in query_lower.split() else 0.6
                    })
                    break
        
        # Detect entities
        entities_found = []
        for entity, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    entities_found.append(entity)
                    themes.append({
                        "type": "entity",
                        "value": entity,
                        "confidence": 0.9
                    })
                    break
        
        return themes
    
    def normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching"""
        # Lowercase, remove extra spaces, basic stemming
        normalized = query.lower().strip()
        normalized = ' '.join(normalized.split())  # Remove extra spaces
        return normalized


class UserMemoryService:
    """Manage long-term user memory and profiles"""
    
    def __init__(self):
        self.interest_detector = InterestDetectionService()
    
    async def get_or_create_profile(
        self, 
        user_id: str, 
        tenant_id: str
    ) -> UserProfile:
        """Get existing profile or create new one"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(
                    and_(
                        UserProfile.user_id == user_id,
                        UserProfile.tenant_id == tenant_id
                    )
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = UserProfile(
                    id=self._generate_id(),
                    user_id=user_id,
                    tenant_id=tenant_id,
                    interests=[],
                    memory_summary="New user. No history yet."
                )
                session.add(profile)
                await session.commit()
            
            return profile
    
    async def record_interaction(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        sql: Optional[str] = None,
        response_summary: Optional[str] = None,
        chart_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        row_count: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> UserInteraction:
        """Record a new user interaction"""
        
        # Detect themes
        themes = self.interest_detector.detect_themes(query)
        entities = [t["value"] for t in themes if t["type"] == "entity"]
        
        async with AsyncSessionLocal() as session:
            interaction = UserInteraction(
                id=self._generate_id(),
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=session_id,
                query=query,
                normalized_query=self.interest_detector.normalize_query(query),
                sql_generated=sql,
                response_summary=response_summary,
                chart_type=chart_type,
                themes=[t["value"] for t in themes],
                entities_mentioned=entities,
                execution_time_ms=execution_time_ms,
                row_count=row_count
            )
            
            session.add(interaction)
            await session.commit()
            
            return interaction
    
    async def consolidate_memory(
        self,
        user_id: str,
        tenant_id: str,
        lookback_days: int = 7
    ) -> UserProfile:
        """Update user memory based on recent interactions"""
        
        async with AsyncSessionLocal() as session:
            profile = await self.get_or_create_profile(user_id, tenant_id)
            
            # Get recent interactions
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            result = await session.execute(
                select(UserInteraction).where(
                    and_(
                        UserInteraction.user_id == user_id,
                        UserInteraction.tenant_id == tenant_id,
                        UserInteraction.created_at >= cutoff
                    )
                ).order_by(desc(UserInteraction.created_at))
            )
            interactions = result.scalars().all()
            
            if not interactions:
                return profile
            
            # Analyze patterns
            theme_counts: Dict[str, int] = {}
            entity_counts: Dict[str, int] = {}
            chart_types: Set[str] = set()
            
            for interaction in interactions:
                for theme in interaction.themes:
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1
                
                for entity in interaction.entities_mentioned:
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
                
                if interaction.chart_type:
                    chart_types.add(interaction.chart_type)
            
            # Update interests (keep top 10)
            sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
            interests = [
                {
                    "topic": theme,
                    "frequency": count,
                    "category": self._categorize_theme(theme),
                    "confidence": min(count / len(interactions) * 2, 1.0)
                }
                for theme, count in sorted_themes[:10]
            ]
            
            profile.interests = interests
            profile.preferred_chart_types = list(chart_types)
            
            # Generate memory summary
            top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            entity_str = ", ".join([e[0] for e in top_entities])
            
            profile.memory_summary = (
                f"User frequently asks about {entity_str}. "
                f"Prefers {', '.join(list(chart_types)[:2]) if chart_types else 'various'} visualizations. "
                f"Active {len(interactions)} times in last {lookback_days} days."
            )
            
            profile.updated_at = datetime.utcnow()
            await session.commit()
            
            return profile
    
    def _categorize_theme(self, theme: str) -> str:
        """Categorize a theme"""
        if theme in [c.value for c in InterestCategory]:
            return theme
        return "entity"
    
    def _generate_id(self) -> str:
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]


class ProactiveIntelligenceService:
    """Generate proactive suggestions based on user memory and new data"""
    
    def __init__(self, db_connector, llm_factory):
        self.db = db_connector
        self.llm = llm_factory
        self.memory_service = UserMemoryService()
    
    async def discover_insights(
        self,
        user_id: str,
        tenant_id: str
    ) -> List[ProactiveSuggestion]:
        """Discover new insights that might interest the user"""
        
        # Get user profile
        profile = await self.memory_service.get_or_create_profile(user_id, tenant_id)
        
        if not profile.interests:
            return []
        
        # Get recent data changes (this would connect to your data pipeline)
        # For now, simulate with pattern-based discovery
        suggestions = []
        
        for interest in profile.interests[:5]:  # Top 5 interests
            topic = interest.get("topic", "")
            
            # Look for anomalies in data related to this topic
            anomaly_suggestions = await self._check_for_anomalies(
                user_id, tenant_id, topic, profile
            )
            suggestions.extend(anomaly_suggestions)
            
            # Check for trends
            trend_suggestions = await self._check_for_trends(
                user_id, tenant_id, topic, profile
            )
            suggestions.extend(trend_suggestions)
        
        # Store suggestions
        await self._store_suggestions(suggestions)
        
        return suggestions
    
    async def _check_for_anomalies(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        profile: UserProfile
    ) -> List[ProactiveSuggestion]:
        """Check for anomalous data related to user's interests"""
        suggestions = []
        
        # This would run anomaly detection queries
        # Simplified example for revenue
        if topic in ['revenue', 'sales']:
            # Query: Check if revenue changed significantly today vs yesterday
            query = f"SELECT DATE(created_at) as date, SUM(amount) as revenue FROM orders WHERE created_at >= DATE('now', '-7 days') GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 2"
            
            # In real implementation, execute query and analyze
            # For now, create placeholder suggestion
            suggestions.append(ProactiveSuggestion(
                id=self._generate_id(),
                user_id=user_id,
                tenant_id=tenant_id,
                title="Revenue Spike Detected",
                description="Your revenue yesterday was 23% higher than average. Want to see what drove it?",
                suggested_query="What drove the revenue spike yesterday?",
                reason="You frequently check revenue metrics. Significant change detected.",
                source_themes=["revenue", "anomalies"],
                new_data_evidence={"change_percent": 23, "direction": "up"},
                priority=ProactivePriority.HIGH,
                created_at=datetime.utcnow()
            ))
        
        return suggestions
    
    async def _check_for_trends(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        profile: UserProfile
    ) -> List[ProactiveSuggestion]:
        """Check for emerging trends"""
        suggestions = []
        
        # Example: Detect upward trend in customer signups
        if topic in ['customers', 'growth']:
            suggestions.append(ProactiveSuggestion(
                id=self._generate_id(),
                user_id=user_id,
                tenant_id=tenant_id,
                title="Customer Growth Accelerating",
                description="New customer acquisition is up 15% this week vs last week.",
                suggested_query="Show me customer acquisition trend this month",
                reason="Based on your interest in customer metrics.",
                source_themes=["customers", "trends"],
                new_data_evidence={"growth_rate": 0.15, "period": "week"},
                priority=ProactivePriority.MEDIUM,
                created_at=datetime.utcnow()
            ))
        
        return suggestions
    
    async def _store_suggestions(self, suggestions: List[ProactiveSuggestion]):
        """Store suggestions in database"""
        async with AsyncSessionLocal() as session:
            for suggestion in suggestions:
                record = ProactiveSuggestionRecord(
                    id=suggestion.id,
                    user_id=suggestion.user_id,
                    tenant_id=suggestion.tenant_id,
                    suggestion_data=suggestion.to_dict(),
                    priority=suggestion.priority.value
                )
                session.add(record)
            await session.commit()
    
    async def get_pending_suggestions(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 10
    ) -> List[ProactiveSuggestion]:
        """Get undelivered suggestions for a user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProactiveSuggestionRecord).where(
                    and_(
                        ProactiveSuggestionRecord.user_id == user_id,
                        ProactiveSuggestionRecord.tenant_id == tenant_id,
                        ProactiveSuggestionRecord.delivered == False,
                        ProactiveSuggestionRecord.dismissed == False
                    )
                ).order_by(
                    text("CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END")
                ).limit(limit)
            )
            
            records = result.scalars().all()
            return [
                ProactiveSuggestion(
                    id=r.id,
                    user_id=r.user_id,
                    tenant_id=r.tenant_id,
                    **r.suggestion_data
                )
                for r in records
            ]
    
    async def mark_delivered(
        self,
        suggestion_id: str,
        channel: str = "in_app"
    ):
        """Mark a suggestion as delivered"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProactiveSuggestionRecord).where(
                    ProactiveSuggestionRecord.id == suggestion_id
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.delivered = True
                record.delivered_at = datetime.utcnow()
                record.delivery_channel = channel
                await session.commit()
    
    def _generate_id(self) -> str:
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]


# Database migration helpers
async def create_user_memory_tables():
    """Create tables if they don't exist"""
    from app.database import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
