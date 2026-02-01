"""
Proactive Intelligence System

Background jobs that analyze user behavior, detect patterns,
generate insights, and deliver proactive suggestions.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import statistics
from collections import defaultdict

from sqlalchemy import select, and_, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from app.database import AsyncSessionLocal
from app.models import (
    UserProfile, QuestionHistory, ProactiveInsight, 
    Dashboard, View, DBConnection
)
from app.config import get_settings
from app.cache import get_redis

settings = get_settings()


class InsightType(str, Enum):
    """Types of proactive insights"""
    ANOMALY = "anomaly"           # Unusual data patterns
    TREND = "trend"               # Emerging trends
    PATTERN = "pattern"           # User behavior patterns
    CORRELATION = "correlation"   # Discovered relationships
    REMINDER = "reminder"         # Time-based reminders
    SUGGESTION = "suggestion"     # Query suggestions


class InsightPriority(str, Enum):
    """Priority levels for insights"""
    HIGH = "high"       # Immediate attention
    MEDIUM = "medium"   # Worth reviewing
    LOW = "low"         # FYI


@dataclass
class Pattern:
    """Detected user pattern"""
    pattern_type: str
    confidence: float
    description: str
    data: Dict[str, Any]
    detected_at: datetime


@dataclass
class Anomaly:
    """Detected data anomaly"""
    metric: str
    current_value: float
    expected_value: float
    deviation_percent: float
    severity: str
    context: Dict[str, Any]


@dataclass
class Suggestion:
    """Generated query suggestion"""
    suggestion_type: str
    text: str
    query: str
    confidence: float
    reason: str


class PatternDetector:
    """Detect patterns in user behavior and data"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
    
    async def analyze_user_patterns(
        self,
        user_id: str,
        tenant_id: str,
        days: int = 30
    ) -> List[Pattern]:
        """Analyze user query patterns"""
        
        async with AsyncSessionLocal() as session:
            # Get user's query history
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = (
                select(QuestionHistory)
                .where(
                    and_(
                        QuestionHistory.user_id == user_id,
                        QuestionHistory.tenant_id == tenant_id,
                        QuestionHistory.created_at >= start_date
                    )
                )
                .order_by(QuestionHistory.created_at)
            )
            
            result = await session.execute(query)
            history = result.scalars().all()
            
            if not history:
                return []
            
            patterns = []
            
            # 1. Temporal patterns
            temporal = self._detect_temporal_patterns(history)
            if temporal:
                patterns.append(temporal)
            
            # 2. Topic patterns
            topic = self._detect_topic_patterns(history)
            if topic:
                patterns.append(topic)
            
            # 3. Sequential patterns
            sequential = self._detect_sequential_patterns(history)
            if sequential:
                patterns.append(sequential)
            
            # 4. Engagement patterns
            engagement = self._detect_engagement_patterns(history)
            if engagement:
                patterns.append(engagement)
            
            return patterns
    
    def _detect_temporal_patterns(
        self,
        history: List[QuestionHistory]
    ) -> Optional[Pattern]:
        """Detect time-based query patterns"""
        
        # Group by hour of day
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        
        for h in history:
            hour_counts[h.created_at.hour] += 1
            day_counts[h.created_at.weekday()] += 1
        
        # Find peak hours
        peak_hours = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Find peak days
        peak_days = sorted(
            day_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        if peak_hours and peak_days:
            return Pattern(
                pattern_type="temporal",
                confidence=0.8,
                description=f"Active {day_names[peak_days[0][0]]}s at {peak_hours[0][0]}:00",
                data={
                    "peak_hours": [h[0] for h in peak_hours],
                    "peak_days": [day_names[d[0]] for d in peak_days],
                    "total_queries": len(history)
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _detect_topic_patterns(
        self,
        history: List[QuestionHistory]
    ) -> Optional[Pattern]:
        """Detect topic interest patterns"""
        
        # Aggregate topics
        topic_counts = defaultdict(int)
        for h in history:
            if h.topics:
                for topic in h.topics:
                    topic_counts[topic] += 1
        
        if not topic_counts:
            return None
        
        # Top topics
        top_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Detect increasing interest
        recent_topics = defaultdict(int)
        older_topics = defaultdict(int)
        
        mid_point = len(history) // 2
        for i, h in enumerate(history):
            if h.topics:
                target = recent_topics if i >= mid_point else older_topics
                for topic in h.topics:
                    target[topic] += 1
        
        # Find trending topics
        trending = []
        for topic, recent_count in recent_topics.items():
            older_count = older_topics.get(topic, 0)
            if recent_count > older_count * 1.5:  # 50% increase
                trending.append(topic)
        
        return Pattern(
            pattern_type="topic",
            confidence=0.75,
            description=f"Interested in: {', '.join([t[0] for t in top_topics[:3]])}",
            data={
                "top_topics": top_topics,
                "trending_topics": trending,
                "topic_diversity": len(topic_counts)
            },
            detected_at=datetime.utcnow()
        )
    
    def _detect_sequential_patterns(
        self,
        history: List[QuestionHistory]
    ) -> Optional[Pattern]:
        """Detect sequential query patterns"""
        
        # Look for common 2-query sequences
        sequences = defaultdict(int)
        
        for i in range(len(history) - 1):
            curr_topics = tuple(sorted(history[i].topics or []))
            next_topics = tuple(sorted(history[i + 1].topics or []))
            
            if curr_topics and next_topics:
                sequences[(curr_topics, next_topics)] += 1
        
        # Find frequent sequences
        frequent = [
            (seq, count) for seq, count in sequences.items()
            if count >= 2
        ]
        
        if frequent:
            frequent.sort(key=lambda x: x[1], reverse=True)
            return Pattern(
                pattern_type="sequential",
                confidence=0.7,
                description=f"Common follow-up patterns detected",
                data={
                    "frequent_sequences": frequent[:3],
                    "sequence_count": len(sequences)
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _detect_engagement_patterns(
        self,
        history: List[QuestionHistory]
    ) -> Optional[Pattern]:
        """Detect engagement patterns"""
        
        # Calculate query frequency trend
        if len(history) < 7:
            return None
        
        # Group by week
        weekly_counts = defaultdict(int)
        for h in history:
            week = h.created_at.isocalendar()[1]
            weekly_counts[week] += 1
        
        weeks = sorted(weekly_counts.keys())
        if len(weeks) < 2:
            return None
        
        counts = [weekly_counts[w] for w in weeks]
        
        # Detect trend
        if len(counts) >= 3:
            recent_avg = statistics.mean(counts[-2:])
            older_avg = statistics.mean(counts[:-2])
            
            change = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            if change > 0.2:
                trend = "increasing"
            elif change < -0.2:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return Pattern(
                pattern_type="engagement",
                confidence=0.75,
                description=f"Engagement is {trend}",
                data={
                    "trend": trend,
                    "change_percent": change * 100,
                    "avg_queries_per_week": statistics.mean(counts)
                },
                detected_at=datetime.utcnow()
            )
        
        return None


class AnomalyDetector:
    """Detect anomalies in tracked metrics"""
    
    async def detect_metric_anomalies(
        self,
        connection_id: str,
        metric: str,
        table: str,
        column: str,
        aggregation: str = "SUM"
    ) -> List[Anomaly]:
        """Detect anomalies in a specific metric"""
        
        from app.database.executor import QueryExecutor
        from app.database.connector import DatabaseConfig
        
        # Build trend query
        trend_query = f"""
            SELECT 
                DATE_TRUNC('day', created_at) as date,
                {aggregation}({column}) as value
            FROM {table}
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY 1
            ORDER BY 1
        """
        
        # Execute query
        # TODO: Get actual connection config
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="demo",
            username="postgres",
            password="postgres"
        )
        
        executor = QueryExecutor()
        result = await executor.execute(trend_query, config)
        
        if not result["success"]:
            return []
        
        data = result["data"]["rows"]
        if len(data) < 7:  # Need at least a week of data
            return []
        
        anomalies = []
        
        # Calculate statistics
        values = [row["value"] for row in data]
        mean = statistics.mean(values[:-1])  # Exclude today
        std_dev = statistics.stdev(values[:-1]) if len(values) > 2 else 0
        
        if std_dev == 0:
            return []
        
        # Check recent values
        recent_values = values[-3:]  # Last 3 days
        
        for i, value in enumerate(recent_values):
            z_score = (value - mean) / std_dev
            
            if abs(z_score) > 2:  # 2 standard deviations
                deviation = (value - mean) / mean * 100
                
                anomalies.append(Anomaly(
                    metric=f"{aggregation}({column})",
                    current_value=value,
                    expected_value=mean,
                    deviation_percent=deviation,
                    severity="high" if abs(z_score) > 3 else "medium",
                    context={
                        "date": data[-3 + i]["date"],
                        "z_score": z_score,
                        "table": table,
                        "column": column
                    }
                ))
        
        return anomalies


class SuggestionEngine:
    """Generate personalized query suggestions"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_api_key,
            temperature=0.3,
            api_key=settings.openai_api_key
        )
    
    async def generate_suggestions(
        self,
        user_id: str,
        tenant_id: str,
        patterns: List[Pattern],
        context: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate personalized suggestions based on patterns"""
        
        suggestions = []
        
        # 1. Time-based suggestions
        time_suggestion = self._generate_time_suggestion(patterns, context)
        if time_suggestion:
            suggestions.append(time_suggestion)
        
        # 2. Topic-based suggestions
        topic_suggestions = self._generate_topic_suggestions(patterns, context)
        suggestions.extend(topic_suggestions)
        
        # 3. Follow-up suggestions
        follow_up = await self._generate_follow_up_suggestions(user_id, tenant_id)
        if follow_up:
            suggestions.append(follow_up)
        
        # 4. Trending suggestions
        trending = await self._generate_trending_suggestions(tenant_id)
        if trending:
            suggestions.append(trending)
        
        return suggestions[:5]  # Return top 5
    
    def _generate_time_suggestion(
        self,
        patterns: List[Pattern],
        context: Dict[str, Any]
    ) -> Optional[Suggestion]:
        """Generate time-based suggestion"""
        
        temporal = next(
            (p for p in patterns if p.pattern_type == "temporal"),
            None
        )
        
        if not temporal:
            return None
        
        peak_hours = temporal.data.get("peak_hours", [])
        current_hour = datetime.utcnow().hour
        
        # If user is active now and usually checks something
        if current_hour in peak_hours:
            return Suggestion(
                suggestion_type="pattern",
                text="You usually check metrics around this time",
                query="What are the key metrics today?",
                confidence=0.8,
                reason=f"Based on your activity at {current_hour}:00"
            )
        
        return None
    
    def _generate_topic_suggestions(
        self,
        patterns: List[Pattern],
        context: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate topic-based suggestions"""
        
        topic_pattern = next(
            (p for p in patterns if p.pattern_type == "topic"),
            None
        )
        
        if not topic_pattern:
            return []
        
        suggestions = []
        trending = topic_pattern.data.get("trending_topics", [])
        top_topics = topic_pattern.data.get("top_topics", [])[:3]
        
        # Suggest exploring trending topics
        if trending:
            suggestions.append(Suggestion(
                suggestion_type="trend",
                text=f"You've been asking more about {trending[0]} recently",
                query=f"Show me {trending[0]} trends over time",
                confidence=0.75,
                reason="50% increase in recent queries"
            ))
        
        # Suggest related topics
        if len(top_topics) >= 2:
            suggestions.append(Suggestion(
                suggestion_type="exploration",
                text=f"Explore relationship between {top_topics[0][0]} and {top_topics[1][0]}",
                query=f"How does {top_topics[0][0]} correlate with {top_topics[1][0]}?",
                confidence=0.7,
                reason="Both are topics of interest"
            ))
        
        return suggestions
    
    async def _generate_follow_up_suggestions(
        self,
        user_id: str,
        tenant_id: str
    ) -> Optional[Suggestion]:
        """Generate follow-up on recent queries"""
        
        async with AsyncSessionLocal() as session:
            # Get recent unanswered or interesting queries
            query = (
                select(QuestionHistory)
                .where(
                    and_(
                        QuestionHistory.user_id == user_id,
                        QuestionHistory.tenant_id == tenant_id
                    )
                )
                .order_by(desc(QuestionHistory.created_at))
                .limit(1)
            )
            
            result = await session.execute(query)
            recent = result.scalar_one_or_none()
            
            if not recent:
                return None
            
            # If query was about time-series data, suggest comparing periods
            if recent.topics and 'revenue' in [t.lower() for t in recent.topics]:
                return Suggestion(
                    suggestion_type="follow_up",
                    text="Compare to previous period?",
                    query="How does this compare to last month?",
                    confidence=0.7,
                    reason="Natural follow-up to revenue analysis"
                )
            
            return None
    
    async def _generate_trending_suggestions(
        self,
        tenant_id: str
    ) -> Optional[Suggestion]:
        """Generate suggestions based on org-wide trends"""
        
        # Get popular queries across organization
        async with AsyncSessionLocal() as session:
            query = (
                select(
                    QuestionHistory.question_text,
                    func.count(QuestionHistory.id).label('count')
                )
                .where(QuestionHistory.tenant_id == tenant_id)
                .group_by(QuestionHistory.question_text)
                .order_by(desc('count'))
                .limit(5)
            )
            
            result = await session.execute(query)
            popular = result.fetchall()
            
            if popular:
                return Suggestion(
                    suggestion_type="popular",
                    text="Your team frequently asks about this",
                    query=popular[0][0],
                    confidence=0.6,
                    reason=f"Asked {popular[0][1]} times by your team"
                )
            
            return None


class ProactiveInsightGenerator:
    """Generate and deliver proactive insights"""
    
    def __init__(self):
        self.pattern_detector = PatternDetector()
        self.anomaly_detector = AnomalyDetector()
        self.suggestion_engine = SuggestionEngine()
    
    async def generate_insights_for_user(
        self,
        user_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Generate all proactive insights for a user"""
        
        insights = []
        
        # 1. Detect patterns
        patterns = await self.pattern_detector.analyze_user_patterns(
            user_id, tenant_id
        )
        
        # 2. Generate suggestions
        suggestions = await self.suggestion_engine.generate_suggestions(
            user_id, tenant_id, patterns, {}
        )
        
        for suggestion in suggestions:
            insights.append({
                "type": InsightType.SUGGESTION,
                "title": suggestion.text,
                "description": suggestion.reason,
                "suggested_query": suggestion.query,
                "confidence": suggestion.confidence,
                "priority": InsightPriority.MEDIUM
            })
        
        # 3. Check for data anomalies (if we have tracked metrics)
        # TODO: Implement metric tracking
        
        return insights
    
    async def deliver_insight(
        self,
        user_id: str,
        tenant_id: str,
        insight: Dict[str, Any]
    ) -> str:
        """Store and queue insight for delivery"""
        
        async with AsyncSessionLocal() as session:
            # Create insight record
            db_insight = ProactiveInsight(
                tenant_id=tenant_id,
                user_id=user_id,
                insight_type=insight["type"],
                title=insight["title"],
                description=insight.get("description"),
                suggested_question=insight.get("suggested_query"),
                status="pending",
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            
            session.add(db_insight)
            await session.commit()
            
            # Cache for real-time delivery
            redis = await get_redis()
            await redis.lpush(
                f"insights:{user_id}",
                str(db_insight.id)
            )
            
            return str(db_insight.id)
    
    async def get_pending_insights(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get pending insights for delivery"""
        
        async with AsyncSessionLocal() as session:
            query = (
                select(ProactiveInsight)
                .where(
                    and_(
                        ProactiveInsight.user_id == user_id,
                        ProactiveInsight.status == "pending",
                        ProactiveInsight.expires_at > datetime.utcnow()
                    )
                )
                .order_by(desc(ProactiveInsight.created_at))
                .limit(limit)
            )
            
            result = await session.execute(query)
            insights = result.scalars().all()
            
            return [
                {
                    "id": str(i.id),
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "suggested_query": i.suggested_question,
                    "created_at": i.created_at.isoformat()
                }
                for i in insights
            ]
    
    async def mark_insight_delivered(self, insight_id: str):
        """Mark insight as delivered"""
        
        async with AsyncSessionLocal() as session:
            query = (
                select(ProactiveInsight)
                .where(ProactiveInsight.id == insight_id)
            )
            result = await session.execute(query)
            insight = result.scalar_one_or_none()
            
            if insight:
                insight.status = "delivered"
                insight.delivered_at = datetime.utcnow()
                await session.commit()
    
    async def record_feedback(
        self,
        insight_id: str,
        feedback: str  # 'helpful', 'not_helpful', 'irrelevant'
    ):
        """Record user feedback on insight"""
        
        async with AsyncSessionLocal() as session:
            query = (
                select(ProactiveInsight)
                .where(ProactiveInsight.id == insight_id)
            )
            result = await session.execute(query)
            insight = result.scalar_one_or_none()
            
            if insight:
                insight.user_feedback = feedback
                insight.viewed_at = datetime.utcnow()
                await session.commit()


class UserProfileUpdater:
    """Update user profiles based on behavior analysis"""
    
    async def update_profile(
        self,
        user_id: str,
        tenant_id: str
    ):
        """Update user profile with detected patterns"""
        
        # Detect patterns
        detector = PatternDetector()
        patterns = await detector.analyze_user_patterns(user_id, tenant_id)
        
        async with AsyncSessionLocal() as session:
            # Get or create profile
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
                from app.models import UserProfile
                profile = UserProfile(
                    tenant_id=tenant_id,
                    user_id=user_id
                )
                session.add(profile)
            
            # Update based on patterns
            for pattern in patterns:
                if pattern.pattern_type == "temporal":
                    profile.active_hours = pattern.data.get("peak_hours", [])
                    profile.active_days = [
                        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].index(d)
                        for d in pattern.data.get("peak_days", [])
                    ]
                
                elif pattern.pattern_type == "topic":
                    profile.top_topics = [
                        {"topic": t[0], "count": t[1]}
                        for t in pattern.data.get("top_topics", [])
                    ]
                
                elif pattern.pattern_type == "engagement":
                    # Infer role based on engagement
                    avg_queries = pattern.data.get("avg_queries_per_week", 0)
                    if avg_queries > 20:
                        profile.inferred_role = "power_user"
                    elif avg_queries > 5:
                        profile.inferred_role = "regular_user"
                    else:
                        profile.inferred_role = "occasional_user"
            
            # Update query count
            count_query = (
                select(func.count(QuestionHistory.id))
                .where(
                    and_(
                        QuestionHistory.user_id == user_id,
                        QuestionHistory.tenant_id == tenant_id
                    )
                )
            )
            count_result = await session.execute(count_query)
            profile.total_questions = count_result.scalar()
            
            profile.updated_at = datetime.utcnow()
            await session.commit()


# Background job runners
async def run_pattern_detection():
    """Background job: Detect patterns for all users"""
    
    updater = UserProfileUpdater()
    
    async with AsyncSessionLocal() as session:
        # Get all active users
        query = (
            select(QuestionHistory.user_id, QuestionHistory.tenant_id)
            .distinct()
        )
        result = await session.execute(query)
        users = result.fetchall()
        
        for user_id, tenant_id in users:
            try:
                await updater.update_profile(user_id, tenant_id)
                print(f"Updated profile for user {user_id}")
            except Exception as e:
                print(f"Error updating profile for {user_id}: {e}")


async def run_insight_generation():
    """Background job: Generate proactive insights"""
    
    generator = ProactiveInsightGenerator()
    
    async with AsyncSessionLocal() as session:
        # Get active users
        query = (
            select(QuestionHistory.user_id, QuestionHistory.tenant_id)
            .where(
                QuestionHistory.created_at >= datetime.utcnow() - timedelta(days=7)
            )
            .distinct()
        )
        result = await session.execute(query)
        users = result.fetchall()
        
        for user_id, tenant_id in users:
            try:
                # Generate insights
                insights = await generator.generate_insights_for_user(
                    user_id, tenant_id
                )
                
                # Deliver insights
                for insight in insights:
                    await generator.deliver_insight(user_id, tenant_id, insight)
                
                print(f"Generated {len(insights)} insights for user {user_id}")
                
            except Exception as e:
                print(f"Error generating insights for {user_id}: {e}")


async def run_anomaly_detection():
    """Background job: Detect data anomalies"""
    
    detector = AnomalyDetector()
    
    # TODO: Get list of tracked metrics from configuration
    # For now, placeholder
    pass
