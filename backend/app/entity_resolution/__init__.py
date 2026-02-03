"""
Entity Resolution System

Automated value-level entity resolution for natural language to SQL.

Usage:
    from app.entity_resolution import EntityResolver, onboard_database
    
    # One-command onboarding
    result = await onboard_database(db_connection, "ClientName")
    
    # Resolve entity mentions
    resolver = EntityResolver(result.index, result.abbreviations)
    result = await resolver.resolve("LBG", "revenue for LBG")
    
    if result.requires_clarification:
        print(result.clarification_question)
    else:
        print(f"Matched: {result.match.canonical_value}")
"""

from app.entity_resolution.profiler import (
    DatabaseProfiler,
    DatabaseProfile,
    ColumnProfile,
    TableProfile,
    EntityType
)

from app.entity_resolution.indexer import (
    ValueIndexer,
    ValueIndex,
    ValueEntry,
    VariationGenerator
)

from app.entity_resolution.abbreviations import (
    AbbreviationLearner,
    AbbreviationRule
)

from app.entity_resolution.resolver import (
    EntityResolver,
    ResolutionResult,
    QueryContext,
    IntentAnalyzer,
    UserPreferenceStore,
    ValueMatch
)

from app.entity_resolution.onboarding import (
    ClientOnboarding,
    OnboardingResult,
    onboard_database
)

__all__ = [
    # Profiler
    'DatabaseProfiler',
    'DatabaseProfile',
    'ColumnProfile', 
    'TableProfile',
    'EntityType',
    
    # Indexer
    'ValueIndexer',
    'ValueIndex',
    'ValueEntry',
    'ValueMatch',
    'VariationGenerator',
    
    # Abbreviations
    'AbbreviationLearner',
    'AbbreviationRule',
    
    # Resolver
    'EntityResolver',
    'ResolutionResult',
    'QueryContext',
    'IntentAnalyzer',
    'UserPreferenceStore',
    
    # Onboarding
    'ClientOnboarding',
    'OnboardingResult',
    'onboard_database',
]

__version__ = "1.0.0"
