# Prompt Engineering Guide

## Overview

This guide covers the prompt engineering practices used in the AI Analytics Platform for optimal natural language to SQL conversion and intelligent query handling.

## Architecture

### Prompt Registry System

The platform uses a centralized **Prompt Registry** for managing all LLM prompts:

```python
from app.prompts.registry import get_prompt, PromptType, register_prompt

# Get a prompt template
prompt = get_prompt("sql_generator", PromptType.SQL_GENERATION, version="2.0")

# Render with variables
rendered = prompt.render(
    dialect="postgresql",
    schema_context=schema_info,
    query=user_query
)
```

### Prompt Types

1. **INTENT_CLASSIFICATION** - Classify user query intent
2. **SQL_GENERATION** - Generate SQL from natural language
3. **ENTITY_EXTRACTION** - Extract entities (metrics, dimensions, filters)
4. **CLARIFICATION** - Generate clarification questions
5. **INSIGHT_GENERATION** - Generate insights from results
6. **QUERY_SUGGESTION** - Suggest related queries
7. **RESPONSE_FORMATTING** - Format natural language responses

## Best Practices

### 1. Few-Shot Prompting

Include relevant examples to improve accuracy:

```python
FEW_SHOT_EXAMPLES = [
    {
        "query": "What was revenue yesterday?",
        "intent": "simple",
        "reasoning": "Single metric, specific time"
    },
    # ... more examples
]
```

**Guidelines:**
- Use 3-8 examples depending on complexity
- Include diverse examples covering edge cases
- Show reasoning, not just answers
- Update examples based on production performance

### 2. Schema-Aware Prompting

Always include relevant schema context:

```python
schema_context = """
Table: orders
  - id (INTEGER): Order ID
  - total (DECIMAL): Order total amount
  - created_at (TIMESTAMP): Order creation time
  - user_id (INTEGER): Reference to users

Table: users
  - id (INTEGER): User ID
  - email (VARCHAR): User email
  - created_at (TIMESTAMP): Account creation
"""
```

**Best Practices:**
- Include column types for type-safe SQL
- Add descriptions for semantic understanding
- Include relationships and foreign keys
- Limit to relevant tables (top 5-10)

### 3. Structured Output

Require structured JSON output for reliable parsing:

```json
{
    "sql": "SELECT ...",
    "explanation": "What this query does",
    "chart_type": "line|bar|table",
    "confidence": 0.0-1.0,
    "parameters": ["dynamic params"]
}
```

### 4. Chain-of-Thought Reasoning

For complex tasks, require step-by-step reasoning:

```
STEP 1: Identify entities needed
STEP 2: Determine time range
STEP 3: Plan joins
STEP 4: Write SQL
```

## Prompt Versions

### A/B Testing

Test different prompt versions:

```python
# Set active version for testing
from app.prompts.registry import _registry

_registry.set_active_version(
    name="sql_generator",
    prompt_type=PromptType.SQL_GENERATION,
    version="2.0"  # Test new version
)
```

### Version Management

- **v1.0**: Basic functionality
- **v2.0**: Enhanced with examples and reasoning
- Track performance metrics per version
- Gradual rollout based on accuracy

## Optimization Techniques

### 1. Context Compression

Keep prompts concise:

```python
# Good - concise
"Available tables: orders(id, total, created_at), users(id, email)"

# Avoid - verbose
"The orders table has an id column which is an integer..."
```

### 2. Dynamic Context Selection

Select relevant context dynamically:

```python
# Use embeddings to find relevant schema
relevant_tables = vector_search(query_embedding, schema_embeddings, k=5)
```

### 3. Multi-Turn Context

Include conversation history for follow-ups:

```python
conversation = """
User: What was revenue last month?
Assistant: Revenue was $100K
User: And this month?  # Follow-up
"""
```

## Error Handling

### Fallback Strategies

1. **Pattern Matching** - Fast-path for common queries
2. **Simplified Prompt** - Retry with minimal context
3. **Clarification** - Ask user for more details

```python
async def generate_with_fallback(query):
    try:
        # Try enhanced prompt
        return await generate_enhanced(query)
    except:
        try:
            # Fallback to simple prompt
            return await generate_simple(query)
        except:
            # Request clarification
            return ask_clarification()
```

## Performance Tuning

### Temperature Settings

- **0.0-0.2**: SQL generation (deterministic)
- **0.3-0.5**: Insights (some creativity)
- **0.7-0.9**: Suggestions (diverse options)

### Token Optimization

```python
# Limit schema size
if len(schema_context) > 2000:
    schema_context = compress_schema(schema_context)
```

## Testing Prompts

### Unit Tests

```python
def test_intent_classification():
    result = classify_intent("What was revenue yesterday?")
    assert result.intent == IntentType.SIMPLE
    assert result.confidence > 0.8
```

### Evaluation Framework

Track metrics:
- SQL accuracy (execution success)
- Intent classification accuracy
- User satisfaction ratings
- Response relevance

## Security Considerations

### Prompt Injection Prevention

```python
# Sanitize user input
query = sanitize_input(user_query)

# Never include raw user input in system prompts
```

### SQL Injection Prevention

- Validate generated SQL before execution
- Use parameterized queries
- Apply allowlists for tables/columns

## LangChain Integration

### Using LangChain Components

```python
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a SQL expert."),
    ("human", "{query}")
])

chain = prompt | ChatOpenAI() | JsonOutputParser()
```

### Custom Output Parsers

```python
from langchain.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=SQLGenerationResult)
prompt = prompt.partial(format_instructions=parser.get_format_instructions())
```

## OpenAI Function Calling

### Function Definitions

```python
functions = [{
    "name": "generate_sql",
    "description": "Generate SQL from natural language",
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
            "explanation": {"type": "string"}
        },
        "required": ["sql"]
    }
}]
```

## Monitoring and Analytics

### Track Prompt Performance

```python
# Log prompt versions and results
log_prompt_metrics(
    prompt_version="2.0",
    query_type="simple",
    success=True,
    latency_ms=450
)
```

### Key Metrics

- **Success Rate** - % of successful SQL generation
- **Accuracy** - Correctness of generated SQL
- **Latency** - Response time
- **Token Usage** - Cost efficiency
- **User Satisfaction** - Feedback ratings

## Future Improvements

### Planned Enhancements

1. **Adaptive Prompts** - Adjust based on user feedback
2. **Multi-Model Ensemble** - Combine multiple LLM outputs
3. **Prompt Chaining** - Multi-step reasoning workflows
4. **Auto-Prompt Optimization** - ML-based prompt tuning
5. **Domain-Specific Prompts** - Industry-specific templates

## References

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [Vercel AI SDK](https://sdk.vercel.ai/docs)
- [Awesome Prompt Engineering](https://github.com/promptslab/Awesome-Prompt-Engineering)
