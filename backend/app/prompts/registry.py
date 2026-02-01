"""
Centralized Prompt Management System

Features:
- Template management with Jinja2-style variables
- Prompt versioning for A/B testing
- Dynamic prompt selection based on context
- Prompt performance tracking
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime


class PromptType(Enum):
    """Types of prompts for categorization"""
    INTENT_CLASSIFICATION = "intent_classification"
    SQL_GENERATION = "sql_generation"
    ENTITY_EXTRACTION = "entity_extraction"
    RESPONSE_FORMATTING = "response_formatting"
    CLARIFICATION = "clarification"
    INSIGHT_GENERATION = "insight_generation"
    QUERY_SUGGESTION = "query_suggestion"


@dataclass
class PromptTemplate:
    """A prompt template with metadata"""
    name: str
    type: PromptType
    version: str
    template: str
    description: str
    variables: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    performance_score: Optional[float] = None
    usage_count: int = 0
    
    def render(self, **kwargs) -> str:
        """Render the template with provided variables"""
        result = self.template
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def validate_variables(self, **kwargs) -> List[str]:
        """Check if all required variables are provided"""
        missing = []
        for var in self.variables:
            if var not in kwargs:
                missing.append(var)
        return missing


class PromptRegistry:
    """Registry for managing prompt templates"""
    
    def __init__(self):
        self._prompts: Dict[str, List[PromptTemplate]] = {}
        self._active_versions: Dict[str, str] = {}
    
    def register(self, prompt: PromptTemplate, is_default: bool = False):
        """Register a prompt template"""
        key = f"{prompt.type.value}:{prompt.name}"
        
        if key not in self._prompts:
            self._prompts[key] = []
        
        self._prompts[key].append(prompt)
        
        if is_default or prompt.version == "1.0":
            self._active_versions[key] = prompt.version
    
    def get(
        self, 
        name: str, 
        prompt_type: PromptType, 
        version: Optional[str] = None
    ) -> PromptTemplate:
        """Get a prompt template by name and version"""
        key = f"{prompt_type.value}:{name}"
        
        if key not in self._prompts:
            raise KeyError(f"Prompt '{key}' not found")
        
        prompts = self._prompts[key]
        
        if version:
            for p in prompts:
                if p.version == version:
                    return p
            raise KeyError(f"Version '{version}' not found for prompt '{key}'")
        
        # Return active version
        active_version = self._active_versions.get(key, "1.0")
        for p in prompts:
            if p.version == active_version:
                return p
        
        # Fallback to latest
        return prompts[-1]
    
    def list_versions(self, name: str, prompt_type: PromptType) -> List[str]:
        """List all versions of a prompt"""
        key = f"{prompt_type.value}:{name}"
        if key not in self._prompts:
            return []
        return [p.version for p in self._prompts[key]]
    
    def set_active_version(self, name: str, prompt_type: PromptType, version: str):
        """Set the active version for A/B testing"""
        key = f"{prompt_type.value}:{name}"
        available_versions = self.list_versions(name, prompt_type)
        if version not in available_versions:
            raise ValueError(f"Version '{version}' not available. Options: {available_versions}")
        self._active_versions[key] = version
    
    def get_by_type(self, prompt_type: PromptType) -> List[PromptTemplate]:
        """Get all prompts of a specific type"""
        results = []
        for key, prompts in self._prompts.items():
            if key.startswith(f"{prompt_type.value}:"):
                results.extend(prompts)
        return results


# Global registry instance
_registry = PromptRegistry()


def register_prompt(prompt: PromptTemplate, is_default: bool = False):
    """Register a prompt template globally"""
    _registry.register(prompt, is_default)


def get_prompt(
    name: str, 
    prompt_type: PromptType, 
    version: Optional[str] = None
) -> PromptTemplate:
    """Get a prompt template from global registry"""
    return _registry.get(name, prompt_type, version)


def render_prompt(
    name: str,
    prompt_type: PromptType,
    version: Optional[str] = None,
    **kwargs
) -> str:
    """Get and render a prompt in one call"""
    prompt = get_prompt(name, prompt_type, version)
    return prompt.render(**kwargs)


# ============================================================
# INTENT CLASSIFICATION PROMPTS
# ============================================================

INTENT_CLASSIFICATION_V1 = PromptTemplate(
    name="intent_classifier",
    type=PromptType.INTENT_CLASSIFICATION,
    version="1.0",
    description="Basic intent classification with reasoning",
    variables=["query", "conversation_history"],
    template="""Analyze this question and classify the intent.

Conversation History:
{{conversation_history}}

Current Question: "{{query}}"

Classify as one of:
- "simple": Direct lookup (single metric, specific time range)
- "complex": Analysis requiring multiple joins/aggregations
- "investigate": Exploratory ("why", "what caused", "compare", "trend")
- "clarify": Ambiguous, missing context, or unclear intent
- "follow_up": Refers to previous results ("and last month?", "what about X?")
- "correction": User correcting or refining a previous query

Consider:
1. Is the query clear and specific?
2. Does it reference previous conversation?
3. What type of analysis is needed?
4. Are all required entities (metrics, dimensions, time) specified?

Respond with JSON:
{
    "intent": "simple|complex|investigate|clarify|follow_up|correction",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of classification",
    "missing_context": ["list of missing info if clarify"],
    "referenced_entities": ["entities from history if follow_up"],
    "suggested_clarification": "question to ask user if needed"
}"""
)

INTENT_CLASSIFICATION_V2 = PromptTemplate(
    name="intent_classifier",
    type=PromptType.INTENT_CLASSIFICATION,
    version="2.0",
    description="Enhanced intent classification with ambiguity detection",
    variables=["query", "conversation_history", "user_profile"],
    template="""You are an expert at understanding user intent in analytics queries.

User Profile:
{{user_profile}}

Conversation History:
{{conversation_history}}

Current Question: "{{query}}"

Analyze the intent using these categories:

INTENT TYPES:
- "simple": Single metric lookup (e.g., "What was revenue yesterday?")
- "complex": Multi-dimensional analysis (e.g., "Revenue by product and region")
- "investigate": Root cause, correlation, or deep analysis (e.g., "Why did revenue drop?")
- "clarify": Missing critical information (time range, metric definition, filters)
- "follow_up": Builds on previous query ("and compared to last month?", "show me top 10")
- "correction": User fixing or changing previous request
- "greeting": Casual greeting ("hello", "hi there")
- "meta": About the system itself ("what can you do?", "how do I...")

AMBIGUITY DETECTION:
Check for these ambiguous patterns:
- Vague metrics ("performance", "numbers", "results")
- Missing time periods (no explicit date/time reference)
- Unclear aggregation ("show sales" - by what? sum? count?)
- Multiple possible interpretations

Respond with JSON:
{
    "intent": "simple|complex|investigate|clarify|follow_up|correction|greeting|meta",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation",
    "ambiguity_level": "none|low|medium|high",
    "ambiguities": [
        {
            "type": "metric|time|dimension|filter",
            "description": "what's unclear",
            "possible_interpretations": ["option1", "option2"]
        }
    ],
    "missing_context": ["specific missing info"],
    "referenced_entities": ["entities carried from history"],
    "suggested_clarification": "specific question to resolve ambiguity",
    "suggested_queries": ["alternative query interpretations"]
}"""
)

# ============================================================
# SQL GENERATION PROMPTS
# ============================================================

SQL_GENERATION_V1 = PromptTemplate(
    name="sql_generator",
    type=PromptType.SQL_GENERATION,
    version="1.0",
    description="Schema-aware SQL generation with few-shot examples",
    variables=[
        "dialect", "schema_context", "few_shot_examples", 
        "semantic_definitions", "conversation_history", "query"
    ],
    template="""You are an expert SQL analyst. Generate {{dialect}} SQL from natural language.

DATABASE SCHEMA:
{{schema_context}}

BUSINESS DEFINITIONS:
{{semantic_definitions}}

SIMILAR PAST QUERIES (Few-Shot Examples):
{{few_shot_examples}}

CONVERSATION HISTORY:
{{conversation_history}}

USER QUESTION: "{{query}}"

GENERATION RULES:
1. Use ONLY tables and columns from the schema
2. Always include appropriate time filters (don't return all historical data)
3. Use explicit JOIN conditions with table aliases
4. Include meaningful column aliases using AS
5. Add ORDER BY for rankings and time series
6. Use LIMIT appropriately (default 100, max 1000)
7. Handle NULLs explicitly (COALESCE, NULLIF)
8. Use proper type casting for comparisons
9. Optimize for readability and performance

For time calculations in {{dialect}}:
- Current date: CURRENT_DATE
- Date arithmetic: Use appropriate date functions
- Time zones: Assume UTC unless specified

Respond with JSON:
{
    "sql": "SELECT ...",
    "explanation": "what the query does",
    "chart_type": "line|bar|table|pie|metric|scatter|area",
    "x_column": "column for x-axis",
    "y_column": "column for y-axis",
    "time_column": "date/time column if time series",
    "confidence": 0.0-1.0,
    "parameters": ["any dynamic parameters"],
    "optimization_notes": ["query optimization hints"],
    "alternative_queries": ["other ways to answer this"]
}"""
)

SQL_GENERATION_V2 = PromptTemplate(
    name="sql_generator",
    type=PromptType.SQL_GENERATION,
    version="2.0",
    description="Advanced SQL generation with multi-turn reasoning",
    variables=[
        "dialect", "schema_context", "few_shot_examples",
        "semantic_definitions", "conversation_history", "query",
        "extracted_entities", "user_preferences"
    ],
    template="""You are a senior data engineer generating {{dialect}} SQL.

STEP 1: UNDERSTAND THE REQUEST
Extracted Entities: {{extracted_entities}}
User Preferences: {{user_preferences}}

STEP 2: REVIEW CONTEXT
Database Schema:
{{schema_context}}

Business Terminology:
{{semantic_definitions}}

Relevant Examples:
{{few_shot_examples}}

Conversation Context:
{{conversation_history}}

STEP 3: QUERY ANALYSIS
User Question: "{{query}}"

Determine:
- What metrics need calculation?
- What dimensions for grouping?
- What time range applies?
- What filters are needed?
- Are there any joins required?
- What aggregations (SUM, AVG, COUNT, etc.)?

STEP 4: GENERATE OPTIMIZED SQL
Rules:
1. ONLY use schema tables/columns
2. Prefer CTEs (WITH clauses) for complex logic
3. Add appropriate indexes hints if relevant
4. Use window functions for rankings/running totals
5. Include comments for complex logic
6. Handle edge cases (division by zero, nulls)
7. Apply row limits (LIMIT/TOP)
8. Format with consistent indentation

Anti-patterns to AVOID:
- SELECT * (always specify columns)
- Implicit joins (use explicit JOIN syntax)
- Functions on indexed columns in WHERE
- Missing GROUP BY columns
- Unbounded date ranges

Respond with JSON:
{
    "analysis": {
        "entities_needed": ["table.column"],
        "time_range": "description",
        "aggregations": ["SUM(amount)"],
        "filters": ["conditions"],
        "joins": ["tables to join"]
    },
    "sql": "WITH ... SELECT ...",
    "explanation": "detailed explanation",
    "chart_type": "line|bar|table|pie|metric|scatter|area|funnel",
    "columns": {
        "x_axis": "column name",
        "y_axis": "column name",
        "category": "grouping column",
        "time_column": "date column"
    },
    "confidence": 0.0-1.0,
    "performance_notes": ["optimization suggestions"],
    "assumptions_made": ["assumptions"],
    "alternative_approaches": ["other SQL options"]
}"""
)

# ============================================================
# ENTITY EXTRACTION PROMPTS
# ============================================================

ENTITY_EXTRACTION_V1 = PromptTemplate(
    name="entity_extractor",
    type=PromptType.ENTITY_EXTRACTION,
    version="1.0",
    description="Extract entities from natural language queries",
    variables=["query", "available_metrics", "available_dimensions"],
    template="""Extract entities from this analytics query.

Available Metrics: {{available_metrics}}
Available Dimensions: {{available_dimensions}}

Query: "{{query}}"

Extract:
1. Metrics (what to measure)
2. Dimensions (how to group/slice)
3. Time expressions (when)
4. Filters (conditions)
5. Aggregations (how to calculate)
6. Sorting (order by)
7. Limits (how many results)

TIME EXPRESSION HANDLING:
- "today", "yesterday" -> relative dates
- "this week", "last week" -> week periods
- "this month", "last month" -> month periods
- "Q1", "Q2", "Q3", "Q4" -> quarters
- "YTD", "MTD" -> year/month to date
- "last N days/weeks/months" -> rolling periods
- "2024-01-01 to 2024-01-31" -> absolute range

Respond with JSON:
{
    "metrics": [
        {
            "name": "revenue",
            "matched_to": "orders.total",
            "aggregation": "SUM",
            "alias": "total_revenue"
        }
    ],
    "dimensions": [
        {
            "name": "by product",
            "matched_to": "products.name",
            "is_time_based": false
        }
    ],
    "time_range": {
        "type": "relative|absolute|rolling|period",
        "description": "last 7 days",
        "start_date": "2024-01-01",
        "end_date": "2024-01-07",
        "grain": "day|week|month|quarter|year"
    },
    "filters": [
        {
            "column": "region",
            "operator": "=",
            "value": "North America",
            "logic": "AND"
        }
    ],
    "sort": {
        "column": "revenue",
        "direction": "DESC"
    },
    "limit": 10,
    "confidence": 0.0-1.0
}"""
)

# ============================================================
# CLARIFICATION PROMPTS
# ============================================================

CLARIFICATION_V1 = PromptTemplate(
    name="clarification_generator",
    type=PromptType.CLARIFICATION,
    version="1.0",
    description="Generate clarification questions for ambiguous queries",
    variables=["query", "ambiguities", "conversation_history", "user_preferences"],
    template="""Generate helpful clarification questions for an ambiguous query.

User Query: "{{query}}"

Detected Ambiguities:
{{ambiguities}}

Conversation History:
{{conversation_history}}

User Preferences:
{{user_preferences}}

Generate:
1. A friendly clarification question
2. Multiple choice options when applicable
3. Suggested completions
4. Examples of what the user might mean

Respond with JSON:
{
    "clarification_question": "friendly question to ask user",
    "question_type": "open_ended|multiple_choice|disambiguation",
    "options": [
        {
            "label": "Option text",
            "value": "machine readable value",
            "preview": "what this would query"
        }
    ],
    "suggested_queries": [
        "clarified version 1",
        "clarified version 2"
    ],
    "help_text": "explanation to help the user",
    "examples": ["example queries"]
}"""
)

# ============================================================
# INSIGHT GENERATION PROMPTS
# ============================================================

INSIGHT_GENERATION_V1 = PromptTemplate(
    name="insight_generator",
    type=PromptType.INSIGHT_GENERATION,
    version="1.0",
    description="Generate insights from query results",
    variables=["query", "results_summary", "previous_results", "user_context"],
    template="""Analyze query results and generate actionable insights.

Original Query: "{{query}}"

User Context: {{user_context}}

Previous Related Results:
{{previous_results}}

Current Results Summary:
{{results_summary}}

Generate insights that are:
- Specific and data-backed
- Actionable (what should be done?)
- Contextual (compared to benchmarks/history)
- Prioritized (most important first)

INSIGHT TYPES TO CONSIDER:
1. Trends (up/down, accelerating/decelerating)
2. Anomalies (unexpected values, outliers)
3. Comparisons (vs last period, vs target, vs average)
4. Correlations (relationships between metrics)
5. Segmentation (which groups drive changes)
6. Recommendations (what actions to take)

COMPARATIVE LANGUAGE:
- "up 23% vs last month" (use actual percentages)
- "exceeded target by $50K"
- "3x higher than the average"
- "lowest in 6 months"
- "trending upward for 3 consecutive weeks"

Respond with JSON:
{
    "executive_summary": "2-3 sentence overview",
    "key_insights": [
        {
            "type": "trend|anomaly|comparison|correlation|segmentation",
            "title": "concise headline",
            "description": "detailed explanation with numbers",
            "impact": "high|medium|low",
            "confidence": 0.0-1.0
        }
    ],
    "comparisons": [
        {
            "metric": "name",
            "current_value": "value",
            "previous_value": "value",
            "change_percent": 23.5,
            "change_description": "up 23% vs last month"
        }
    ],
    "anomalies": [
        {
            "description": "what's unusual",
            "severity": "high|medium|low",
            "suspected_cause": "possible explanation"
        }
    ],
    "recommendations": [
        {
            "action": "what to do",
            "rationale": "why this helps",
            "expected_impact": "quantified if possible"
        }
    ],
    "follow_up_questions": [
        "related questions to explore"
    ]
}"""
)

# ============================================================
# QUERY SUGGESTION PROMPTS
# ============================================================

QUERY_SUGGESTION_V1 = PromptTemplate(
    name="query_suggester",
    type=PromptType.QUERY_SUGGESTION,
    version="1.0",
    description="Generate query suggestions and auto-completions",
    variables=["partial_query", "user_history", "popular_queries", "available_entities"],
    template="""Generate intelligent query suggestions.

User's Partial Input: "{{partial_query}}"

Available Entities:
{{available_entities}}

User's Query History:
{{user_history}}

Popular Queries:
{{popular_queries}}

Generate suggestions that are:
1. Relevant to the partial input
2. Based on user's patterns
3. Popular/common queries
4. Contextually appropriate

SUGGESTION TYPES:
- Auto-complete (finish the current query)
- Did-you-mean (correct possible typos/errors)
- Related (similar queries)
- Next-step (follow-up to recent queries)
- Template (common patterns)

Respond with JSON:
{
    "auto_completions": [
        {
            "text": "completed query text",
            "highlight": "the part being added",
            "category": "metric|dimension|time|filter"
        }
    ],
    "did_you_mean": [
        {
            "original": "what user typed",
            "suggestion": "corrected version",
            "reason": "why this is better"
        }
    ],
    "related_queries": [
        {
            "query": "related question",
            "context": "when to use this"
        }
    ],
    "templates": [
        {
            "template": "Show me {metric} by {dimension} for {time}",
            "example": "Show me revenue by product for last month",
            "variables": ["metric", "dimension", "time"]
        }
    ],
    "next_steps": [
        {
            "query": "follow-up question",
            "based_on": "what recent query this extends"
        }
    ]
}"""
)

# ============================================================
# RESPONSE FORMATTING PROMPTS
# ============================================================

RESPONSE_FORMATTING_V1 = PromptTemplate(
    name="response_formatter",
    type=PromptType.RESPONSE_FORMATTING,
    version="1.0",
    description="Format natural language responses",
    variables=["query", "results", "insights", "viz_config", "user_preferences"],
    template="""Format a natural language response to an analytics query.

User Query: "{{query}}"

Visualization Config: {{viz_config}}

User Preferences: {{user_preferences}}

Query Results: {{results}}

Generated Insights: {{insights}}

Create a response that:
1. Directly answers the question
2. Provides context and numbers
3. Uses conversational but professional tone
4. Highlights key findings
5. Suggests follow-ups naturally

RESPONSE STRUCTURE:
- Opening: Direct answer
- Details: Key numbers and context
- Insights: What the data means
- Follow-ups: Natural next questions

Respond with JSON:
{
    "opening": "direct answer to the query",
    "details": "supporting details with numbers",
    "insights_text": "interpretation of the data",
    "follow_up_suggestions": [
        {
            "question": "natural follow-up question",
            "type": "drill_down|comparison|trend|related"
        }
    ],
    "tone": "conversational|formal|technical",
    "full_response": "complete formatted response"
}"""
)


# ============================================================
# REGISTER ALL PROMPTS
# ============================================================

def register_all_prompts():
    """Register all prompt templates in the global registry"""
    
    # Intent classification
    register_prompt(INTENT_CLASSIFICATION_V1, is_default=True)
    register_prompt(INTENT_CLASSIFICATION_V2)
    
    # SQL generation
    register_prompt(SQL_GENERATION_V1, is_default=True)
    register_prompt(SQL_GENERATION_V2)
    
    # Entity extraction
    register_prompt(ENTITY_EXTRACTION_V1, is_default=True)
    
    # Clarification
    register_prompt(CLARIFICATION_V1, is_default=True)
    
    # Insight generation
    register_prompt(INSIGHT_GENERATION_V1, is_default=True)
    
    # Query suggestions
    register_prompt(QUERY_SUGGESTION_V1, is_default=True)
    
    # Response formatting
    register_prompt(RESPONSE_FORMATTING_V1, is_default=True)


# Auto-register on import
register_all_prompts()
