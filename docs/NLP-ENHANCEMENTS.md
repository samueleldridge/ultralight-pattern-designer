# NLP & Prompt Engineering Enhancements

## Summary

This release introduces comprehensive NLP and Prompt Engineering improvements to the AI Analytics Platform, significantly enhancing the accuracy, context awareness, and user experience of natural language to SQL conversion.

## New Features

### 1. Better SQL Generation ✓

**Few-Shot Prompting**
- Template-based prompt system with examples
- Dynamic example selection based on query similarity
- Improved SQL accuracy through demonstrated patterns

**Schema-Aware Prompting**
- Detailed schema context including column types and descriptions
- Relationship awareness for JOIN optimization
- Automatic table/column validation

**Query Optimization Hints**
- CTE (Common Table Expression) recommendations
- Index usage suggestions
- Performance notes included in generation

**Multi-Turn Conversation Support**
- Context resolution for follow-up queries
- Reference handling ("and last month?", "what about X?")
- Conversation memory across queries

### 2. Intent Classification ✓

**Enhanced classify_intent_node**
- Few-shot learning with curated examples
- Confidence scoring for each classification
- Support for 8 intent types:
  - `simple` - Direct lookups
  - `complex` - Multi-dimensional analysis
  - `investigate` - Root cause analysis
  - `clarify` - Ambiguous queries
  - `follow_up` - Contextual continuations
  - `correction` - Query refinement
  - `greeting` - Casual interactions
  - `meta` - System questions

**Ambiguity Detection**
- Automatic detection of vague metrics
- Missing time period identification
- Unclear aggregation detection
- Multiple interpretation handling

**Clarification Questions**
- Smart question generation for ambiguous queries
- Multiple choice options when applicable
- Suggested query completions

### 3. Context Management ✓

**Conversation Memory**
- Full conversation history tracking
- Query context persistence
- Result summaries for future reference

**Contextual Follow-ups**
- Automatic resolution of "it", "that", "this" references
- Time shift detection ("and last month?")
- Dimension addition detection ("break it down by X")
- Filter change handling

**Multi-Query Sessions**
- Session-based context management
- Cross-query entity tracking
- Pattern detection across sessions

### 4. Entity Extraction ✓

**Comprehensive Entity Types**
- Metrics (what to measure)
- Dimensions (how to group)
- Time expressions (when)
- Filters (conditions)
- Aggregations (calculations)
- Sorting preferences
- Result limits

**Date Parsing**
- Relative dates: "today", "yesterday", "last week"
- Period expressions: "this month", "Q1", "YTD"
- Rolling periods: "last 30 days", "past 3 months"
- Absolute ranges: "2024-01-01 to 2024-01-31"
- Business quarters with automatic calculation

**Business Terminology**
- Metric synonym recognition
- Dimension name matching
- Custom business definitions

### 5. Query Suggestions ✓

**Auto-Complete**
- Real-time query completion
- Metric/dimension-aware suggestions
- Common query pattern recognition

**Query Templates**
- Pre-built templates for common patterns:
  - `metric_over_time` - Trend analysis
  - `metric_by_dimension` - Breakdowns
  - `top_n` - Rankings
  - `compare_periods` - Comparisons
  - `growth_rate` - Growth analysis

**"Did You Mean?"**
- Typo detection and correction
- Similar query matching
- Fuzzy string matching

**Related Questions**
- Context-aware suggestions
- Pattern-based recommendations
- User history analysis

### 6. Response Formatting ✓

**Natural Language Summaries**
- Executive summaries of query results
- Detailed explanations with context
- Conversational tone adaptation

**Insight Generation**
- Automatic trend detection
- Anomaly identification
- Comparative analysis ("up 23% vs last month")
- Segmentation insights

**Comparative Analysis**
- Period-over-period calculations
- Percentage change formatting
- Direction indicators (up/down/stable)

**Anomaly Detection**
- IQR-based outlier detection
- Z-score analysis
- Change point detection
- Severity classification

### 7. Prompt Library ✓

**Centralized Prompt Management**
- Single registry for all prompts
- Template versioning system
- Dynamic variable substitution

**A/B Testing Support**
- Version switching for experiments
- Performance tracking per version
- Gradual rollout capabilities

**Prompt Versioning**
- Semantic versioning (v1.0, v2.0)
- Backward compatibility
- Version comparison

**Template System**
- Jinja2-style variable substitution
- Conditional rendering
- Nested template support

## File Structure

```
backend/app/
├── prompts/
│   ├── __init__.py
│   └── registry.py          # Centralized prompt management
├── nlp/
│   ├── __init__.py
│   ├── entity_extraction.py # Entity and date extraction
│   ├── intent_classification.py  # Intent detection
│   ├── context_management.py     # Conversation context
│   ├── query_suggestions.py      # Query suggestions
│   └── response_formatting.py    # Response formatting
└── agent/nodes/
    ├── classify_enhanced.py      # Enhanced classification
    ├── generate_enhanced.py      # Enhanced SQL generation
    ├── analyze_enhanced.py       # Enhanced analysis
    └── workflow_enhanced.py      # Enhanced workflow
docs/
└── prompt-engineering.md     # Comprehensive guide
```

## API Endpoints

### Suggestions API

```
GET /api/suggestions/autocomplete?q={query}
GET /api/suggestions/did-you-mean?q={query}
GET /api/suggestions/templates?category={category}
GET /api/suggestions/related?q={query}
GET /api/suggestions/next-steps?q={query}
GET /api/suggestions/all?q={query}
GET /api/suggestions/similar?q={query}
GET /api/suggestions/popular?category={category}
GET /api/suggestions/time-parsing?expression={expression}
```

## Usage Examples

### Intent Classification

```python
from app.nlp.intent_classification import classify_intent

classification = await classify_intent(
    query="What was revenue last month?",
    conversation_history=[],
    user_profile={}
)

print(classification.intent)  # IntentType.SIMPLE
print(classification.confidence)  # 0.95
```

### Entity Extraction

```python
from app.nlp.entity_extraction import extract_entities

entities = await extract_entities(
    query="Show me top 10 products by revenue for last 30 days",
    schema_context={}
)

print(entities.metrics)  # [revenue]
print(entities.time_range.description)  # "last 30 days"
print(entities.limit)  # 10
```

### Query Suggestions

```python
from app.nlp.query_suggestions import get_query_suggestions

suggestions = await get_query_suggestions(
    partial_query="show me rev",
    user_id="user_123"
)

print(suggestions["auto_completions"])
print(suggestions["did_you_mean"])
```

### Context Resolution

```python
from app.nlp.context_management import resolve_query_context

resolved_query, metadata = await resolve_query_context(
    query="And what about this month?",
    session_id="sess_123",
    user_id="user_123",
    tenant_id="tenant_456"
)

print(resolved_query)  # "What was revenue this month?"
print(metadata["resolution"])  # Resolution details
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
MOONSHOT_API_KEY=...

# Prompt Versioning
ACTIVE_PROMPT_VERSION=2.0

# Context Management
MAX_CONVERSATION_HISTORY=20
SESSION_TIMEOUT_HOURS=24
```

### Prompt Selection

```python
from app.prompts.registry import get_prompt, PromptType

# Get specific version
prompt = get_prompt("sql_generator", PromptType.SQL_GENERATION, version="2.0")

# Use active version (default)
prompt = get_prompt("sql_generator", PromptType.SQL_GENERATION)
```

## Performance Metrics

Expected improvements:
- SQL accuracy: +15-25%
- Intent classification: +20%
- Follow-up handling: +40%
- User satisfaction: +30%

## Migration Guide

### From Previous Versions

1. Update imports:
```python
# Old
from app.agent.nodes.classify import classify_intent_node

# New
from app.agent.nodes.classify_enhanced import classify_intent_node
```

2. Use enhanced workflow:
```python
# Old
from app.agent.workflow import workflow_app

# New
from app.agent.workflow_enhanced import enhanced_workflow_app
```

3. Update API calls:
```python
# Suggestions API unchanged
# New endpoints available for advanced features
```

## Testing

### Unit Tests

```python
def test_intent_classification():
    result = classify_intent("What was revenue yesterday?")
    assert result.intent == IntentType.SIMPLE
    assert result.confidence > 0.8
```

### Integration Tests

```python
async def test_end_to_end():
    result = await enhanced_workflow_app.ainvoke({
        "query": "Show me sales by region",
        "user_id": "test_user",
        "tenant_id": "test_tenant"
    })
    assert result["sql"] is not None
    assert result["insights"] is not None
```

## Best Practices

1. **Use entity extraction before SQL generation** for better context
2. **Leverage conversation sessions** for multi-turn queries
3. **Track prompt performance** to optimize versions
4. **Cache common entity patterns** for faster extraction
5. **Log ambiguity cases** to improve classification

## Future Roadmap

- Multi-language support
- Domain-specific prompt tuning
- Reinforcement learning from feedback
- Custom entity recognition training
- Advanced visualization recommendations
