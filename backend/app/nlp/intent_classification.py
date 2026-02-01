"""
Enhanced Intent Classification Module

Improves classify_intent_node with:
- Better accuracy through few-shot examples
- Ambiguity detection
- Follow-up query detection
- Clarification question generation
"""

import json
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from enum import Enum

from app.llm_provider import get_llm_provider
from app.prompts.registry import get_prompt, PromptType


class IntentType(Enum):
    """Types of user intents"""
    SIMPLE = "simple"
    COMPLEX = "complex"
    INVESTIGATE = "investigate"
    CLARIFY = "clarify"
    FOLLOW_UP = "follow_up"
    CORRECTION = "correction"
    GREETING = "greeting"
    META = "meta"


class AmbiguityLevel(Enum):
    """Levels of query ambiguity"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Ambiguity:
    """Detected ambiguity in query"""
    type: str  # metric, time, dimension, filter
    description: str
    possible_interpretations: List[str] = field(default_factory=list)


@dataclass
class IntentClassification:
    """Result of intent classification"""
    intent: IntentType
    confidence: float
    reasoning: str
    ambiguity_level: AmbiguityLevel
    ambiguities: List[Ambiguity] = field(default_factory=list)
    missing_context: List[str] = field(default_factory=list)
    referenced_entities: List[str] = field(default_factory=list)
    suggested_clarification: Optional[str] = None
    suggested_queries: List[str] = field(default_factory=list)
    is_follow_up: bool = False
    references_previous: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "ambiguity_level": self.ambiguity_level.value,
            "ambiguities": [
                {
                    "type": a.type,
                    "description": a.description,
                    "possible_interpretations": a.possible_interpretations
                }
                for a in self.ambiguities
            ],
            "missing_context": self.missing_context,
            "referenced_entities": self.referenced_entities,
            "suggested_clarification": self.suggested_clarification,
            "suggested_queries": self.suggested_queries,
            "is_follow_up": self.is_follow_up,
            "references_previous": self.references_previous
        }


class IntentClassifier:
    """Enhanced intent classifier with few-shot learning"""
    
    # Few-shot examples for better accuracy
    FEW_SHOT_EXAMPLES = [
        {
            "query": "What was revenue yesterday?",
            "intent": "simple",
            "reasoning": "Single metric (revenue), specific time (yesterday), no aggregation needed"
        },
        {
            "query": "Show me sales by product and region for the last 30 days",
            "intent": "complex",
            "reasoning": "Multiple dimensions (product, region), time range (last 30 days), requires grouping"
        },
        {
            "query": "Why did revenue drop last month?",
            "intent": "investigate",
            "reasoning": "Asking for root cause analysis, requires drilling down and comparing"
        },
        {
            "query": "How are we doing?",
            "intent": "clarify",
            "reasoning": "Ambiguous - no specific metric or time period specified"
        },
        {
            "query": "And what about the previous month?",
            "intent": "follow_up",
            "reasoning": "References previous query context, uses 'and' connector"
        },
        {
            "query": "Actually, I meant total sales not revenue",
            "intent": "correction",
            "reasoning": "User correcting a previous query, uses 'actually' and 'meant'"
        },
        {
            "query": "Compare this quarter to Q1",
            "intent": "complex",
            "reasoning": "Explicit comparison between two time periods, requires calculation"
        },
        {
            "query": "What caused the spike in traffic on Tuesday?",
            "intent": "investigate",
            "reasoning": "Root cause analysis for an anomaly"
        },
        {
            "query": "Show top 10 customers",
            "intent": "simple",
            "reasoning": "Clear metric (customers), clear aggregation (top 10), time not specified but implied current"
        },
        {
            "query": "Can you analyze performance?",
            "intent": "clarify",
            "reasoning": "Vague metric ('performance'), no time period, unclear what to measure"
        },
        {
            "query": "Break it down by channel",
            "intent": "follow_up",
            "reasoning": "'it' refers to previous query, adding dimension"
        },
        {
            "query": "What trends do you see in conversion rates?",
            "intent": "investigate",
            "reasoning": "Looking for patterns over time, requires trend analysis"
        }
    ]
    
    # Pattern-based detection for fast-path classification
    FOLLOW_UP_INDICATORS = [
        'and ', 'also ', 'what about', 'how about', 'compared to',
        'versus', 'vs ', 'add ', 'include ', 'break it down',
        'drill down', 'show me', 'what', 'previous', 'last time',
        'that', 'those', 'it', 'them', 'earlier result'
    ]
    
    CORRECTION_INDICATORS = [
        'actually', 'i meant', 'i meant to', 'not that',
        'wrong', 'instead', 'rather', 'change', 'correct'
    ]
    
    INVESTIGATE_INDICATORS = [
        'why', 'what caused', 'reason', 'explain', 'analyze',
        'trend', 'pattern', 'correlation', 'compare', 'difference'
    ]
    
    AMBIGUOUS_PATTERNS = {
        'vague_metrics': ['performance', 'numbers', 'results', 'metrics', 'data', 'stats'],
        'missing_time': lambda q: not any(t in q.lower() for t in [
            'today', 'yesterday', 'this', 'last', 'past', 'week', 'month',
            'year', 'day', 'date', 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
            'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'q1', 'q2', 'q3', 'q4',
            '2023', '2024', '2025'
        ]),
    }
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or get_llm_provider()
    
    async def classify(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None
    ) -> IntentClassification:
        """Classify the intent of a user query"""
        
        # Pre-process for follow-up detection
        is_follow_up = self._detect_follow_up(query, conversation_history)
        is_correction = self._detect_correction(query)
        
        # Fast-path for obvious patterns
        fast_intent = self._fast_classify(query, is_follow_up, is_correction)
        if fast_intent and not self._is_ambiguous(query):
            return fast_intent
        
        # Use LLM for detailed classification
        llm_result = await self._classify_with_llm(query, conversation_history, user_profile)
        
        # Override with pattern detection if confident
        if is_follow_up and llm_result.confidence < 0.8:
            llm_result.intent = IntentType.FOLLOW_UP
            llm_result.is_follow_up = True
            llm_result.references_previous = True
        
        if is_correction:
            llm_result.intent = IntentType.CORRECTION
        
        return llm_result
    
    def _detect_follow_up(self, query: str, conversation_history: Optional[List[Dict]]) -> bool:
        """Detect if query is a follow-up to previous conversation"""
        if not conversation_history:
            return False
        
        query_lower = query.lower()
        
        # Check for follow-up indicators
        for indicator in self.FOLLOW_UP_INDICATORS:
            if indicator in query_lower:
                return True
        
        # Check for pronouns referring to previous context
        pronouns = ['it', 'them', 'those', 'that', 'these']
        words = query_lower.split()
        if any(p in words for p in pronouns):
            return True
        
        # Check if query is very short (likely follow-up)
        if len(query.split()) <= 4 and len(conversation_history) > 0:
            return True
        
        return False
    
    def _detect_correction(self, query: str) -> bool:
        """Detect if query is correcting a previous query"""
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in self.CORRECTION_INDICATORS)
    
    def _fast_classify(
        self,
        query: str,
        is_follow_up: bool,
        is_correction: bool
    ) -> Optional[IntentClassification]:
        """Fast pattern-based classification for obvious cases"""
        query_lower = query.lower()
        
        # Greeting
        if any(g in query_lower for g in ['hello', 'hi ', 'hey', 'good morning', 'good afternoon']):
            return IntentClassification(
                intent=IntentType.GREETING,
                confidence=0.95,
                reasoning="Greeting detected",
                ambiguity_level=AmbiguityLevel.NONE
            )
        
        # Meta
        if any(m in query_lower for m in ['what can you do', 'how do i', 'help me', 'tutorial']):
            return IntentClassification(
                intent=IntentType.META,
                confidence=0.9,
                reasoning="Meta-question about system capabilities",
                ambiguity_level=AmbiguityLevel.NONE
            )
        
        # Simple queries - single metric, specific time
        simple_patterns = [
            r'what (was|is) \w+ (yesterday|today)',
            r'how many \w+ (did we have|were there)',
            r'total \w+ for \w+',
        ]
        import re
        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                return IntentClassification(
                    intent=IntentType.SIMPLE,
                    confidence=0.85,
                    reasoning="Pattern match for simple lookup",
                    ambiguity_level=AmbiguityLevel.LOW
                )
        
        return None
    
    def _is_ambiguous(self, query: str) -> bool:
        """Check if query is ambiguous"""
        query_lower = query.lower()
        
        # Check for vague metrics
        for vague in self.AMBIGUOUS_PATTERNS['vague_metrics']:
            if vague in query_lower:
                return True
        
        # Check for missing time context
        if self.AMBIGUOUS_PATTERNS['missing_time'](query):
            # Very short queries without time are likely ambiguous
            if len(query.split()) < 5:
                return True
        
        return False
    
    async def _classify_with_llm(
        self,
        query: str,
        conversation_history: Optional[List[Dict]],
        user_profile: Optional[Dict]
    ) -> IntentClassification:
        """Use LLM for intent classification with few-shot examples"""
        
        # Build few-shot examples string
        examples_str = "\n\n".join([
            f"Query: \"{ex['query']}\"\nIntent: {ex['intent']}\nReasoning: {ex['reasoning']}"
            for ex in self.FEW_SHOT_EXAMPLES[:8]  # Use top examples
        ])
        
        # Format conversation history
        history_str = ""
        if conversation_history:
            recent = conversation_history[-3:]  # Last 3 messages
            history_str = "\n".join([
                f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.get('content', '')[:100]}"
                for i, msg in enumerate(recent)
            ])
        
        # Get the enhanced prompt template
        prompt_template = get_prompt("intent_classifier", PromptType.INTENT_CLASSIFICATION, version="2.0")
        
        prompt = prompt_template.render(
            query=query,
            conversation_history=history_str or "No previous conversation",
            user_profile=json.dumps(user_profile or {})
        )
        
        # Add few-shot examples to prompt
        prompt += f"\n\nEXAMPLES:\n{examples_str}"
        
        try:
            result = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt="You are an expert at understanding user intent in analytics queries. Be precise and thorough in your analysis."
            )
            
            return self._parse_llm_result(result)
            
        except Exception as e:
            # Fallback to simple classification
            return IntentClassification(
                intent=IntentType.SIMPLE,
                confidence=0.5,
                reasoning=f"Fallback due to error: {str(e)}",
                ambiguity_level=AmbiguityLevel.MEDIUM,
                suggested_clarification="Could you please provide more details about what you're looking for?"
            )
    
    def _parse_llm_result(self, result: Dict) -> IntentClassification:
        """Parse LLM result into IntentClassification"""
        
        intent_str = result.get('intent', 'simple')
        try:
            intent = IntentType(intent_str.lower())
        except ValueError:
            intent = IntentType.SIMPLE
        
        # Parse ambiguities
        ambiguities = []
        for amb in result.get('ambiguities', []):
            ambiguities.append(Ambiguity(
                type=amb.get('type', 'unknown'),
                description=amb.get('description', ''),
                possible_interpretations=amb.get('possible_interpretations', [])
            ))
        
        # Determine ambiguity level
        amb_level_str = result.get('ambiguity_level', 'none')
        try:
            ambiguity_level = AmbiguityLevel(amb_level_str.lower())
        except ValueError:
            ambiguity_level = AmbiguityLevel.NONE
        
        return IntentClassification(
            intent=intent,
            confidence=result.get('confidence', 0.5),
            reasoning=result.get('reasoning', ''),
            ambiguity_level=ambiguity_level,
            ambiguities=ambiguities,
            missing_context=result.get('missing_context', []),
            referenced_entities=result.get('referenced_entities', []),
            suggested_clarification=result.get('suggested_clarification'),
            suggested_queries=result.get('suggested_queries', []),
            is_follow_up=intent == IntentType.FOLLOW_UP,
            references_previous=len(result.get('referenced_entities', [])) > 0
        )
    
    def needs_clarification(self, classification: IntentClassification) -> bool:
        """Determine if clarification is needed based on classification"""
        if classification.intent == IntentType.CLARIFY:
            return True
        if classification.ambiguity_level in [AmbiguityLevel.HIGH, AmbiguityLevel.MEDIUM]:
            return True
        if classification.confidence < 0.6:
            return True
        return False
    
    async def generate_clarification_question(
        self,
        classification: IntentClassification,
        query: str
    ) -> Dict[str, Any]:
        """Generate a clarification question for ambiguous queries"""
        
        prompt_template = get_prompt("clarification_generator", PromptType.CLARIFICATION)
        
        prompt = prompt_template.render(
            query=query,
            ambiguities=json.dumps([{
                "type": a.type,
                "description": a.description,
                "possible_interpretations": a.possible_interpretations
            } for a in classification.ambiguities]),
            conversation_history="",
            user_preferences="{}"
        )
        
        try:
            result = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt="Generate helpful, friendly clarification questions."
            )
            return result
        except Exception:
            # Fallback clarification
            return {
                "clarification_question": classification.suggested_clarification or 
                    "I want to make sure I understand correctly. Could you provide more details?",
                "question_type": "open_ended",
                "options": [],
                "suggested_queries": classification.suggested_queries[:3]
            }


# Convenience function
async def classify_intent(
    query: str,
    conversation_history: Optional[List[Dict]] = None,
    user_profile: Optional[Dict] = None
) -> IntentClassification:
    """Classify the intent of a user query"""
    classifier = IntentClassifier()
    return await classifier.classify(query, conversation_history, user_profile)
