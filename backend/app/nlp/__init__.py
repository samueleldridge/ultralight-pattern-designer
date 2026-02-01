"""
NLP Module for AI Analytics Platform

Provides entity extraction, intent classification, context management,
query suggestions, and response formatting.
"""

from app.nlp.entity_extraction import (
    EntityExtractor,
    DateParser,
    ExtractedEntities,
    ExtractedMetric,
    ExtractedDimension,
    TimeRange,
    FilterCondition,
    extract_entities
)

from app.nlp.intent_classification import (
    IntentClassifier,
    IntentClassification,
    IntentType,
    AmbiguityLevel,
    classify_intent
)

from app.nlp.context_management import (
    ContextResolver,
    MultiQuerySessionManager,
    ConversationSession,
    QueryContext,
    resolve_query_context,
    save_query_context,
    get_session_manager
)

from app.nlp.query_suggestions import (
    QuerySuggestionEngine,
    QueryTemplate,
    get_query_suggestions,
    record_query_for_suggestions,
    find_similar_past_queries,
    get_suggestion_engine
)

from app.nlp.response_formatting import (
    ResponseFormatter,
    Insight,
    InsightType,
    Comparison,
    Anomaly,
    format_query_response,
    generate_insights
)

__all__ = [
    # Entity Extraction
    'EntityExtractor',
    'DateParser',
    'ExtractedEntities',
    'ExtractedMetric',
    'ExtractedDimension',
    'TimeRange',
    'FilterCondition',
    'extract_entities',
    
    # Intent Classification
    'IntentClassifier',
    'IntentClassification',
    'IntentType',
    'AmbiguityLevel',
    'classify_intent',
    
    # Context Management
    'ContextResolver',
    'MultiQuerySessionManager',
    'ConversationSession',
    'QueryContext',
    'resolve_query_context',
    'save_query_context',
    'get_session_manager',
    
    # Query Suggestions
    'QuerySuggestionEngine',
    'QueryTemplate',
    'get_query_suggestions',
    'record_query_for_suggestions',
    'find_similar_past_queries',
    'get_suggestion_engine',
    
    # Response Formatting
    'ResponseFormatter',
    'Insight',
    'InsightType',
    'Comparison',
    'Anomaly',
    'format_query_response',
    'generate_insights',
]
