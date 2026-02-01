"""
Query Suggestions Module

Provides:
- Auto-complete for common queries
- Query templates
- "Did you mean?" suggestions
- Related questions based on context
"""

import json
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import difflib

from app.llm_provider import get_llm_provider
from app.prompts.registry import get_prompt, PromptType


@dataclass
class QueryTemplate:
    """A query template with variables"""
    name: str
    template: str
    variables: List[str]
    example: str
    category: str
    description: str
    usage_count: int = 0
    
    def render(self, **kwargs) -> str:
        """Render the template with variables"""
        result = self.template
        for var in self.variables:
            placeholder = f"{{{var}}}"
            if placeholder in result:
                value = kwargs.get(var, f"[{var}]")
                result = result.replace(placeholder, str(value))
        return result


class QuerySuggestionEngine:
    """Generate intelligent query suggestions"""
    
    # Common query templates
    TEMPLATES = [
        QueryTemplate(
            name="metric_over_time",
            template="Show me {metric} over {time_period}",
            variables=["metric", "time_period"],
            example="Show me revenue over the last 30 days",
            category="trend",
            description="View a metric's trend over time"
        ),
        QueryTemplate(
            name="metric_by_dimension",
            template="What is {metric} by {dimension} for {time_period}?",
            variables=["metric", "dimension", "time_period"],
            example="What is revenue by product for this month?",
            category="breakdown",
            description="Break down a metric by a dimension"
        ),
        QueryTemplate(
            name="top_n",
            template="Show top {n} {dimension} by {metric} for {time_period}",
            variables=["n", "dimension", "metric", "time_period"],
            example="Show top 10 products by revenue for last quarter",
            category="ranking",
            description="Rank items by a metric"
        ),
        QueryTemplate(
            name="compare_periods",
            template="Compare {metric} between {period1} and {period2}",
            variables=["metric", "period1", "period2"],
            example="Compare revenue between this month and last month",
            category="comparison",
            description="Compare metrics across time periods"
        ),
        QueryTemplate(
            name="metric_filter",
            template="What is {metric} for {filter_value} in {time_period}?",
            variables=["metric", "filter_value", "time_period"],
            example="What is revenue for Enterprise customers in Q3?",
            category="filtered",
            description="View metric with specific filter"
        ),
        QueryTemplate(
            name="growth_rate",
            template="What is the growth rate of {metric} {time_period}?",
            variables=["metric", "time_period"],
            example="What is the growth rate of users month over month?",
            category="analysis",
            description="Calculate growth/change rate"
        ),
        QueryTemplate(
            name="total_summary",
            template="What is the total {metric} for {time_period}?",
            variables=["metric", "time_period"],
            example="What is the total revenue for this year?",
            category="summary",
            description="Get a total/summary metric"
        ),
        QueryTemplate(
            name="average_by",
            template="What is the average {metric} by {dimension}?",
            variables=["metric", "dimension"],
            example="What is the average order value by region?",
            category="average",
            description="Calculate averages grouped by dimension"
        ),
    ]
    
    # Common metric synonyms
    METRIC_SYNONYMS = {
        'revenue': ['sales', 'income', 'money', 'earnings', 'proceeds'],
        'orders': ['purchases', 'transactions', 'sales'],
        'users': ['customers', 'clients', 'visitors', 'people'],
        'profit': ['margin', 'earnings', 'net income'],
        'conversion': ['conversion rate', 'convert', 'converted'],
        'clicks': ['click', 'click-through', 'ctr'],
    }
    
    # Common typos and corrections
    COMMON_TYPOS = {
        'reveune': 'revenue',
        'salse': 'sales',
        'custmer': 'customer',
        'revnue': 'revenue',
        'metirc': 'metric',
        'amont': 'amount',
        'todya': 'today',
        'yesterady': 'yesterday',
        'montly': 'monthly',
        'weeek': 'week',
        'prduct': 'product',
        'catgeory': 'category',
    }
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or get_llm_provider()
        self.user_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.popular_queries: List[Dict] = []
    
    async def get_suggestions(
        self,
        partial_query: str,
        user_id: Optional[str] = None,
        conversation_context: Optional[List[Dict]] = None,
        available_metrics: Optional[List[str]] = None,
        available_dimensions: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """Get all types of suggestions for a partial query"""
        
        suggestions = {
            "auto_completions": [],
            "did_you_mean": [],
            "templates": [],
            "related_queries": [],
            "next_steps": []
        }
        
        # Generate auto-completions
        suggestions["auto_completions"] = self._generate_auto_completions(
            partial_query,
            available_metrics or [],
            available_dimensions or []
        )
        
        # Check for typos
        suggestions["did_you_mean"] = self._check_typos(partial_query)
        
        # Generate template suggestions
        suggestions["templates"] = self._suggest_templates(
            partial_query,
            available_metrics or [],
            available_dimensions or []
        )
        
        # Get LLM-powered suggestions
        llm_suggestions = await self._get_llm_suggestions(
            partial_query,
            user_id,
            conversation_context,
            available_metrics,
            available_dimensions
        )
        
        # Merge LLM suggestions
        suggestions["related_queries"].extend(llm_suggestions.get("related_queries", []))
        suggestions["next_steps"].extend(llm_suggestions.get("next_steps", []))
        
        return suggestions
    
    def _generate_auto_completions(
        self,
        partial_query: str,
        available_metrics: List[str],
        available_dimensions: List[str]
    ) -> List[Dict]:
        """Generate auto-completion suggestions"""
        
        completions = []
        partial_lower = partial_query.lower().strip()
        
        # Common query starters
        starters = {
            "show me": ["revenue", "sales", "users", "orders", "growth"],
            "what is": ["the total", "the average", "our", "the"],
            "how many": ["users", "orders", "customers", "transactions"],
            "compare": ["revenue", "sales", "users", "this month", "Q1"],
            "top": ["10", "5", "20", "customers", "products"],
        }
        
        # Check if partial matches a starter
        for starter, completions_list in starters.items():
            if partial_lower.startswith(starter) and len(partial_lower) <= len(starter) + 3:
                for comp in completions_list:
                    completions.append({
                        "text": f"{starter} {comp}",
                        "highlight": comp,
                        "category": "common"
                    })
        
        # Metric completions
        for metric in available_metrics:
            if metric.lower().startswith(partial_lower.split()[-1] if partial_lower else ""):
                # Complete the word
                words = partial_lower.split()
                if words:
                    words[-1] = metric
                    completed = " ".join(words)
                    completions.append({
                        "text": completed,
                        "highlight": metric,
                        "category": "metric"
                    })
        
        # Dimension completions
        for dimension in available_dimensions:
            if dimension.lower().startswith(partial_lower.split()[-1] if partial_lower else ""):
                words = partial_lower.split()
                if words:
                    words[-1] = dimension
                    completed = " ".join(words)
                    completions.append({
                        "text": completed,
                        "highlight": dimension,
                        "category": "dimension"
                    })
        
        # Remove duplicates and limit
        seen = set()
        unique = []
        for c in completions[:10]:
            if c["text"] not in seen:
                seen.add(c["text"])
                unique.append(c)
        
        return unique[:5]
    
    def _check_typos(self, query: str) -> List[Dict]:
        """Check for common typos and suggest corrections"""
        
        corrections = []
        words = query.lower().split()
        
        for word in words:
            # Check common typos
            if word in self.COMMON_TYPOS:
                corrections.append({
                    "original": word,
                    "suggestion": self.COMMON_TYPOS[word],
                    "reason": "Common typo correction"
                })
            else:
                # Fuzzy match against common terms
                for correct, typos in self.COMMON_TYPOS.items():
                    if difflib.SequenceMatcher(None, word, correct).ratio() > 0.8:
                        corrections.append({
                            "original": word,
                            "suggestion": correct,
                            "reason": "Possible typo"
                        })
        
        return corrections
    
    def _suggest_templates(
        self,
        partial_query: str,
        available_metrics: List[str],
        available_dimensions: List[str]
    ) -> List[Dict]:
        """Suggest query templates based on partial input"""
        
        suggestions = []
        partial_lower = partial_query.lower()
        
        # Score templates by relevance
        for template in self.TEMPLATES:
            score = 0
            
            # Check if template keywords are in partial
            if template.category in partial_lower:
                score += 2
            
            # Check for metric mentions
            if any(m in partial_lower for m in available_metrics):
                score += 1
            
            # Check for dimension mentions
            if any(d in partial_lower for d in available_dimensions):
                score += 1
            
            if score > 0:
                # Generate example with available entities
                example_kwargs = {}
                for var in template.variables:
                    if var in ['metric', 'metrics'] and available_metrics:
                        example_kwargs[var] = available_metrics[0]
                    elif var in ['dimension', 'dimensions'] and available_dimensions:
                        example_kwargs[var] = available_dimensions[0]
                    elif var == 'time_period':
                        example_kwargs[var] = "last 30 days"
                    elif var == 'n':
                        example_kwargs[var] = "10"
                    elif var in ['period1', 'period2']:
                        example_kwargs[var] = "this month" if var == 'period1' else "last month"
                    elif var == 'filter_value':
                        example_kwargs[var] = "Enterprise"
                    else:
                        example_kwargs[var] = f"[{var}]"
                
                example = template.render(**example_kwargs)
                
                suggestions.append({
                    "template": template.template,
                    "example": example,
                    "variables": template.variables,
                    "category": template.category,
                    "description": template.description,
                    "score": score
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        return suggestions[:5]
    
    async def _get_llm_suggestions(
        self,
        partial_query: str,
        user_id: Optional[str],
        conversation_context: Optional[List[Dict]],
        available_metrics: Optional[List[str]],
        available_dimensions: Optional[List[str]]
    ) -> Dict[str, List[Dict]]:
        """Get LLM-powered suggestions"""
        
        try:
            prompt_template = get_prompt("query_suggester", PromptType.QUERY_SUGGESTION)
            
            # Get user history
            user_history = self.user_patterns.get(user_id, []) if user_id else []
            
            prompt = prompt_template.render(
                partial_query=partial_query,
                user_history=json.dumps(user_history[-5:]),
                popular_queries=json.dumps(self.popular_queries[:5]),
                available_entities=json.dumps({
                    "metrics": available_metrics or [],
                    "dimensions": available_dimensions or []
                })
            )
            
            result = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt="Generate helpful, relevant query suggestions for an analytics system."
            )
            
            return {
                "related_queries": result.get("related_queries", []),
                "next_steps": result.get("next_steps", [])
            }
            
        except Exception:
            return {"related_queries": [], "next_steps": []}
    
    def record_user_query(self, user_id: str, query: str, intent: Optional[str] = None):
        """Record a user query for pattern learning"""
        self.user_patterns[user_id].append({
            "query": query,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_popular_queries(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get popular queries, optionally filtered by category"""
        queries = self.popular_queries
        
        if category:
            queries = [q for q in queries if q.get("category") == category]
        
        # Sort by popularity
        queries.sort(key=lambda x: x.get("count", 0), reverse=True)
        
        return queries[:limit]
    
    def find_similar_queries(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Find similar past queries"""
        
        all_queries = []
        
        # Add user-specific queries
        if user_id and user_id in self.user_patterns:
            all_queries.extend(self.user_patterns[user_id])
        
        # Add popular queries
        all_queries.extend(self.popular_queries)
        
        # Calculate similarity
        scored = []
        for q in all_queries:
            similarity = difflib.SequenceMatcher(
                None,
                query.lower(),
                q.get("query", "").lower()
            ).ratio()
            
            if similarity > 0.3:  # Threshold
                scored.append({
                    **q,
                    "similarity": similarity
                })
        
        # Sort by similarity
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        
        return scored[:limit]


# Global instance
_suggestion_engine: Optional[QuerySuggestionEngine] = None


def get_suggestion_engine() -> QuerySuggestionEngine:
    """Get global suggestion engine instance"""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = QuerySuggestionEngine()
    return _suggestion_engine


# Convenience functions
async def get_query_suggestions(
    partial_query: str,
    user_id: Optional[str] = None,
    conversation_context: Optional[List[Dict]] = None,
    available_metrics: Optional[List[str]] = None,
    available_dimensions: Optional[List[str]] = None
) -> Dict[str, List[Dict]]:
    """Get query suggestions for a partial query"""
    engine = get_suggestion_engine()
    return await engine.get_suggestions(
        partial_query, user_id, conversation_context,
        available_metrics, available_dimensions
    )


def record_query_for_suggestions(user_id: str, query: str, intent: Optional[str] = None):
    """Record a query for improving future suggestions"""
    engine = get_suggestion_engine()
    engine.record_user_query(user_id, query, intent)


def find_similar_past_queries(query: str, user_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """Find similar past queries"""
    engine = get_suggestion_engine()
    return engine.find_similar_queries(query, user_id, limit)
