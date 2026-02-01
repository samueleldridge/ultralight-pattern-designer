"""
Enhanced Context Management Module

Provides:
- Multi-turn conversation memory
- Contextual follow-up handling
- Reference resolution ("and last month?", "what about X?")
- Session state management
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque
import hashlib

from app.llm_provider import get_llm_provider


@dataclass
class QueryContext:
    """Context for a single query in a conversation"""
    query_id: str
    timestamp: datetime
    query: str
    entities: Dict[str, Any] = field(default_factory=dict)
    sql: Optional[str] = None
    results_summary: Optional[Dict] = None
    visualization_type: Optional[str] = None
    insights: Optional[List[str]] = None
    intent: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "timestamp": self.timestamp.isoformat(),
            "query": self.query,
            "entities": self.entities,
            "sql": self.sql,
            "results_summary": self.results_summary,
            "visualization_type": self.visualization_type,
            "insights": self.insights,
            "intent": self.intent
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QueryContext":
        return cls(
            query_id=data["query_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            query=data["query"],
            entities=data.get("entities", {}),
            sql=data.get("sql"),
            results_summary=data.get("results_summary"),
            visualization_type=data.get("visualization_type"),
            insights=data.get("insights"),
            intent=data.get("intent")
        )


@dataclass
class ConversationSession:
    """A conversation session with full context"""
    session_id: str
    user_id: str
    tenant_id: str
    created_at: datetime
    contexts: deque = field(default_factory=lambda: deque(maxlen=20))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_context(self, context: QueryContext):
        """Add a new query context to the session"""
        self.contexts.append(context)
    
    def get_recent(self, n: int = 3) -> List[QueryContext]:
        """Get the most recent n contexts"""
        return list(self.contexts)[-n:]
    
    def get_by_intent(self, intent: str) -> List[QueryContext]:
        """Get all contexts with a specific intent"""
        return [c for c in self.contexts if c.intent == intent]
    
    def find_referenced_query(self, query: str) -> Optional[QueryContext]:
        """Find the query being referenced by a follow-up"""
        # Check for pronouns and references
        reference_indicators = ['it', 'that', 'those', 'them', 'this', 'these', 'earlier', 'previous', 'last']
        
        query_lower = query.lower()
        has_reference = any(f' {indicator} ' in f' {query_lower} ' or 
                           query_lower.startswith(f'{indicator} ') or
                           query_lower.endswith(f' {indicator}')
                           for indicator in reference_indicators)
        
        if has_reference and self.contexts:
            # Return most recent context
            return self.contexts[-1]
        
        # Check for partial matches in recent queries
        for ctx in reversed(self.contexts):
            # Check if current query is a continuation
            if any(word in query_lower for word in ctx.query.lower().split()):
                return ctx
        
        return None
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "contexts": [c.to_dict() for c in self.contexts],
            "metadata": self.metadata
        }


class ContextResolver:
    """Resolves contextual references in follow-up queries"""
    
    # Patterns that indicate context resolution is needed
    REFERENCE_PATTERNS = {
        'time_shift': [
            r'and\s+(last|previous|next)\s+(week|month|quarter|year)',
            r'compared?\s+to\s+(last|previous)',
            r'vs\.?\s+(last|previous)',
            r'what\s+about\s+(last|previous|next)',
        ],
        'dimension_add': [
            r'break\s+(it|that|this)\s+down\s+by',
            r'group\s+(it|that|this)\s+by',
            r'show\s+(it|that|this)\s+by',
            r'add\s+(\w+)\s+(?:column|dimension)',
        ],
        'filter_change': [
            r'just\s+(?:for|show)\s+(\w+)',
            r'only\s+(?:for|show)\s+(\w+)',
            r'filter\s+(?:to|by)\s+(\w+)',
            r'exclude\s+(\w+)',
        ],
        'metric_change': [
            r'what\s+about\s+(\w+)',
            r'how\s+about\s+(\w+)',
            r'instead\s+(?:of|show)\s+(\w+)',
            r'show\s+(\w+)\s+instead',
        ],
        'drill_down': [
            r'drill\s+down\s+(?:into|on)',
            r'tell\s+me\s+more\s+about',
            r'why\s+(?:is|are|did)',
            r'what\s+caused',
        ]
    }
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or get_llm_provider()
    
    def needs_resolution(self, query: str) -> Tuple[bool, str]:
        """Check if query needs context resolution and what type"""
        import re
        
        query_lower = query.lower()
        
        for resolution_type, patterns in self.REFERENCE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return True, resolution_type
        
        # Check for pronouns referring to previous context
        pronouns = [' it ', ' that ', ' this ', ' them ', ' those ']
        if any(p in f' {query_lower} ' for p in pronouns):
            return True, 'general_reference'
        
        return False, 'none'
    
    async def resolve(
        self,
        query: str,
        session: ConversationSession
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve a contextual query into a full standalone query
        Returns: (resolved_query, resolution_metadata)
        """
        needs_resolution, resolution_type = self.needs_resolution(query)
        
        if not needs_resolution:
            return query, {"resolved": False}
        
        # Get the referenced context
        referenced = session.find_referenced_query(query)
        if not referenced:
            return query, {"resolved": False, "reason": "No referenced context found"}
        
        # Build resolution prompt
        resolution_prompt = self._build_resolution_prompt(
            query, referenced, resolution_type
        )
        
        try:
            result = await self.llm_provider.generate_json(
                prompt=resolution_prompt,
                system_prompt="You are an expert at understanding conversational context in analytics queries. Expand follow-up queries into standalone queries."
            )
            
            resolved_query = result.get('resolved_query', query)
            metadata = {
                "resolved": True,
                "resolution_type": resolution_type,
                "referenced_query_id": referenced.query_id,
                "original_query": query,
                "changes_made": result.get('changes', []),
                "confidence": result.get('confidence', 0.5)
            }
            
            return resolved_query, metadata
            
        except Exception as e:
            # Fallback: simple merge
            resolved = self._simple_merge(query, referenced, resolution_type)
            return resolved, {
                "resolved": True,
                "resolution_type": resolution_type,
                "method": "fallback",
                "error": str(e)
            }
    
    def _build_resolution_prompt(
        self,
        query: str,
        referenced: QueryContext,
        resolution_type: str
    ) -> str:
        """Build a prompt for context resolution"""
        
        return f"""Expand this follow-up query into a complete, standalone query.

RESOLUTION TYPE: {resolution_type}

PREVIOUS QUERY: "{referenced.query}"
Previous entities: {json.dumps(referenced.entities)}
Previous SQL: {referenced.sql or 'N/A'}

FOLLOW-UP QUERY: "{query}"

INSTRUCTIONS:
- Expand "it", "that", "this" into specific references
- Include the time period explicitly
- Include all metrics and dimensions
- Make the query self-contained

Respond with JSON:
{{
    "resolved_query": "the complete standalone query",
    "changes": ["what was added/changed"],
    "confidence": 0.0-1.0
}}"""
    
    def _simple_merge(
        self,
        query: str,
        referenced: QueryContext,
        resolution_type: str
    ) -> str:
        """Simple merge strategy as fallback"""
        
        if resolution_type == 'time_shift':
            # Combine with new time reference
            return f"{referenced.query} ({query})"
        
        elif resolution_type == 'dimension_add':
            # Add dimension to previous query
            return f"{referenced.query}, {query}"
        
        elif resolution_type == 'filter_change':
            # Add filter to previous query
            return f"{referenced.query} with {query}"
        
        else:
            # Default: just combine
            return f"Regarding: {referenced.query}. {query}"


class MultiQuerySessionManager:
    """Manages multi-query sessions with context preservation"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.llm_provider = get_llm_provider()
        self.context_resolver = ContextResolver(self.llm_provider)
    
    def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str
    ) -> ConversationSession:
        """Get existing session or create new one"""
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                created_at=datetime.utcnow()
            )
        
        return self.sessions[session_id]
    
    async def process_query(
        self,
        query: str,
        session_id: str,
        user_id: str,
        tenant_id: str
    ) -> Tuple[str, Dict[str, Any], ConversationSession]:
        """
        Process a query with context resolution
        Returns: (resolved_query, context_metadata, session)
        """
        session = self.get_or_create_session(session_id, user_id, tenant_id)
        
        # Resolve contextual references
        resolved_query, resolution_metadata = await self.context_resolver.resolve(
            query, session
        )
        
        # Build context for the query
        context_metadata = {
            "session_id": session_id,
            "resolution": resolution_metadata,
            "recent_contexts": [c.to_dict() for c in session.get_recent(3)],
            "conversation_summary": self._generate_summary(session)
        }
        
        return resolved_query, context_metadata, session
    
    def add_query_result(
        self,
        session_id: str,
        query: str,
        entities: Dict[str, Any],
        sql: Optional[str] = None,
        results_summary: Optional[Dict] = None,
        visualization_type: Optional[str] = None,
        insights: Optional[List[str]] = None,
        intent: Optional[str] = None
    ) -> str:
        """Add a completed query result to the session"""
        
        if session_id not in self.sessions:
            return ""
        
        session = self.sessions[session_id]
        
        # Generate query ID
        query_id = hashlib.md5(
            f"{session_id}:{query}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]
        
        context = QueryContext(
            query_id=query_id,
            timestamp=datetime.utcnow(),
            query=query,
            entities=entities,
            sql=sql,
            results_summary=results_summary,
            visualization_type=visualization_type,
            insights=insights,
            intent=intent
        )
        
        session.add_context(context)
        
        return query_id
    
    def _generate_summary(self, session: ConversationSession) -> str:
        """Generate a summary of the conversation"""
        if not session.contexts:
            return "No previous queries"
        
        recent = session.get_recent(3)
        topics = set()
        
        for ctx in recent:
            if ctx.entities:
                metrics = ctx.entities.get('metrics', [])
                for m in metrics:
                    if isinstance(m, dict):
                        topics.add(m.get('name', ''))
        
        if topics:
            return f"Recent topics: {', '.join(filter(None, topics))}"
        
        return f"{len(session.contexts)} queries in this session"
    
    def get_session_context(
        self,
        session_id: str,
        include_entities: bool = True,
        include_sql: bool = False
    ) -> Dict[str, Any]:
        """Get formatted context for a session"""
        
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[session_id]
        recent = session.get_recent(5)
        
        context = {
            "session_id": session_id,
            "query_count": len(session.contexts),
            "recent_queries": []
        }
        
        for ctx in recent:
            q_info = {
                "query": ctx.query,
                "timestamp": ctx.timestamp.isoformat(),
                "intent": ctx.intent
            }
            
            if include_entities:
                q_info["entities"] = ctx.entities
            
            if include_sql and ctx.sql:
                q_info["sql"] = ctx.sql
            
            context["recent_queries"].append(q_info)
        
        return context
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than specified hours"""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = [
            sid for sid, session in self.sessions.items()
            if session.created_at < cutoff
        ]
        
        for sid in to_remove:
            del self.sessions[sid]
        
        return len(to_remove)


# Global instance
_session_manager: Optional[MultiQuerySessionManager] = None


def get_session_manager() -> MultiQuerySessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = MultiQuerySessionManager()
    return _session_manager


# Convenience functions
async def resolve_query_context(
    query: str,
    session_id: str,
    user_id: str,
    tenant_id: str
) -> Tuple[str, Dict[str, Any]]:
    """Resolve a query's context and return the expanded query"""
    manager = get_session_manager()
    resolved, metadata, _ = await manager.process_query(
        query, session_id, user_id, tenant_id
    )
    return resolved, metadata


def save_query_context(
    session_id: str,
    query: str,
    entities: Dict[str, Any],
    sql: Optional[str] = None,
    results_summary: Optional[Dict] = None,
    visualization_type: Optional[str] = None,
    insights: Optional[List[str]] = None,
    intent: Optional[str] = None
) -> str:
    """Save a query result to the session context"""
    manager = get_session_manager()
    return manager.add_query_result(
        session_id, query, entities, sql, results_summary,
        visualization_type, insights, intent
    )
