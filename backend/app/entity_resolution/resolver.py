"""
Entity Resolution Engine

Main resolver that combines all strategies:
- User preferences (learned)
- Exact matches
- Abbreviation expansion
- Fuzzy matching
- Semantic similarity
- Context-aware disambiguation
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher

from app.entity_resolution.indexer import ValueIndex, ValueEntry
from app.entity_resolution.abbreviations import AbbreviationLearner


@dataclass
class ValueMatch:
    """A match result from the resolver"""
    entry: ValueEntry
    score: float
    match_type: str  # exact, fuzzy, semantic, abbreviation
    matched_form: str  # The actual form that matched


@dataclass
class QueryContext:
    """Context for a query being resolved"""
    query: str
    user_id: str
    intent: Optional[str] = None
    mentioned_tables: List[str] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)


@dataclass
class ResolutionResult:
    """Final resolution result"""
    match: Optional[ValueEntry]
    confidence: float
    source: str
    requires_clarification: bool
    candidates: List[ValueMatch] = field(default_factory=list)
    clarification_question: Optional[str] = None
    reasoning: str = ""


class IntentAnalyzer:
    """Analyze query intent to guide disambiguation"""
    
    INTENT_PATTERNS = {
        'revenue_analysis': [
            r'revenue', r'sales', r'income', r'earnings', r'profit',
            r'how much', r'total.*money', r'made.*money', r'financial',
            r'revenue.*from', r'earned', r'invoiced', r'billed'
        ],
        'engagement_tracking': [
            r'engagement', r'project', r'campaign', r'initiative',
            r'working on', r'status of', r'progress', r'milestone',
            r'delivery', r'timeline', r'deadline', r'phase'
        ],
        'client_management': [
            r'client', r'customer', r'account', r'relationship',
            r'contact', r'touchpoint', r'account manager', r'rep',
            r'owned by', r'managed by'
        ],
        'performance_review': [
            r'performance', r'metrics', r'kpi', r'how.*doing',
            r'results', r'outcomes', r'achievement', r'target'
        ],
        'company_analysis': [
            r'company', r'organization', r'firm', r'business',
            r'parent company', r'subsidiary', r'acquisition',
            r'merger', r'parent of', r'owned by'
        ]
    }
    
    def analyze(self, query: str) -> Tuple[str, float]:
        """Extract primary intent from query"""
        query_lower = query.lower()
        
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > 0:
                scores[intent] = score / len(patterns)
        
        if not scores:
            return 'unknown', 0.0
        
        # Return top intent
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents[0]
    
    def intent_matches_entity_type(self, intent: str, entity_type: str) -> float:
        """Score how well an intent matches an entity type"""
        mappings = {
            'revenue_analysis': {'client': 0.9, 'company': 0.8, 'product': 0.6},
            'engagement_tracking': {'project': 0.95, 'client': 0.5},
            'client_management': {'client': 0.95, 'company': 0.7},
            'performance_review': {'client': 0.6, 'project': 0.7, 'product': 0.5},
            'company_analysis': {'company': 0.95, 'client': 0.6}
        }
        
        if intent in mappings:
            return mappings[intent].get(entity_type, 0.3)
        return 0.5


class UserPreferenceStore:
    """Store and retrieve user preferences"""
    
    def __init__(self):
        self.preferences: Dict[str, Dict] = {}
        self.clarifications: List[Dict] = []
    
    async def get(self, user_id: str, mention: str, query: str) -> Optional[ResolutionResult]:
        """Get learned preference for this user/mention combination"""
        key = f"{user_id}:{mention.lower()}"
        
        if key in self.preferences:
            pref = self.preferences[key]
            
            # Check if query pattern matches
            if self._pattern_matches(query, pref.get('query_pattern', '')):
                return ResolutionResult(
                    match=pref['match'],
                    confidence=pref['confidence'],
                    source='user_preference',
                    requires_clarification=False,
                    reasoning=f"User previously selected this for '{mention}'"
                )
        
        return None
    
    async def update(self, user_id: str, mention: str, 
                     selected_match: ValueEntry, query: str):
        """Record a user selection"""
        key = f"{user_id}:{mention.lower()}"
        
        self.preferences[key] = {
            'match': selected_match,
            'confidence': 0.95,
            'query_pattern': self._extract_pattern(query),
            'timestamp': datetime.utcnow()
        }
    
    def _extract_pattern(self, query: str) -> str:
        """Extract key pattern from query for matching"""
        # Remove specific entity names, keep structure
        # "revenue from Acme" -> "revenue from [ENTITY]"
        return re.sub(r'\b[A-Z][a-zA-Z\s]+\b', '[ENTITY]', query)
    
    def _pattern_matches(self, query1: str, query2: str) -> bool:
        """Check if two queries have similar patterns"""
        return self._extract_pattern(query1) == self._extract_pattern(query2)
    
    async def record_clarification(self, user_id: str, mention: str,
                                   query: str, selected: ValueEntry,
                                   candidates: List[ValueMatch]):
        """Record a clarification interaction"""
        self.clarifications.append({
            'user_id': user_id,
            'mention': mention.lower(),
            'query': query,
            'selected': selected,
            'candidates': [c.entry.canonical_value for c in candidates],
            'timestamp': datetime.utcnow()
        })


class EntityResolver:
    """Main entity resolution engine"""
    
    def __init__(self, index: ValueIndex, abbreviations: AbbreviationLearner):
        self.index = index
        self.abbreviations = abbreviations
        self.intent_analyzer = IntentAnalyzer()
        self.user_preferences = UserPreferenceStore()
        self.confidence_thresholds = {
            'auto_accept': 0.85,
            'ask_clarification': 0.60
        }
    
    async def resolve(self, mention: str, query: str, 
                      user_id: str = "anonymous") -> ResolutionResult:
        """
        Main resolution entry point
        Cascades through strategies until confident match or clarification needed
        """
        context = QueryContext(
            query=query,
            user_id=user_id,
            intent=self.intent_analyzer.analyze(query)[0]
        )
        
        # Strategy 1: User preferences (learned from past interactions)
        preference = await self.user_preferences.get(user_id, mention, query)
        if preference and preference.confidence > 0.9:
            return preference
        
        # Strategy 2: Exact match with abbreviation expansion
        exact_result = await self._try_exact_match(mention, context)
        if exact_result.confidence > self.confidence_thresholds['auto_accept']:
            return exact_result
        
        # Strategy 3: Fuzzy match (typos, partial matches)
        fuzzy_result = await self._try_fuzzy_match(mention, context)
        if fuzzy_result and fuzzy_result.confidence > self.confidence_thresholds['auto_accept']:
            return fuzzy_result
        
        # Combine all candidates for potential clarification
        all_candidates = self._combine_candidates(
            exact_result.candidates if exact_result else [],
            fuzzy_result.candidates if fuzzy_result else []
        )
        
        # If we have candidates but not confident, try context disambiguation
        if all_candidates:
            disambiguated = await self._disambiguate_with_context(
                all_candidates, context
            )
            if disambiguated.confidence > self.confidence_thresholds['auto_accept']:
                return disambiguated
            
            # If top candidate is above clarification threshold, use it
            if disambiguated.confidence > self.confidence_thresholds['ask_clarification']:
                return ResolutionResult(
                    match=disambiguated.match,
                    confidence=disambiguated.confidence,
                    source='context_disambiguated',
                    requires_clarification=False,
                    reasoning="Best match based on query context"
                )
            
            # Otherwise, request clarification
            return await self._generate_clarification(mention, all_candidates, context)
        
        # No matches found
        return ResolutionResult(
            match=None,
            confidence=0.0,
            source='no_match',
            requires_clarification=False,
            reasoning=f"No matches found for '{mention}'"
        )
    
    async def _try_exact_match(self, mention: str, 
                               context: QueryContext) -> ResolutionResult:
        """Try exact matching including abbreviation expansion"""
        
        # Try direct lookup
        matches = self.index.lookup(mention)
        
        # If no direct match, try abbreviation expansion
        if not matches:
            expanded = self.abbreviations.expand(mention)
            if expanded:
                matches = self.index.lookup(expanded)
        
        if not matches:
            return ResolutionResult(
                match=None,
                confidence=0.0,
                source='exact_none',
                requires_clarification=False,
                candidates=[]
            )
        
        # Single exact match
        if len(matches) == 1:
            return ResolutionResult(
                match=matches[0],
                confidence=0.95,
                source='exact_single',
                requires_clarification=False,
                candidates=[ValueMatch(matches[0], 0.95, 'exact', mention)]
            )
        
        # Multiple exact matches - need disambiguation
        candidates = [
            ValueMatch(m, 0.9, 'exact', mention) for m in matches
        ]
        
        return ResolutionResult(
            match=None,
            confidence=0.7,
            source='exact_ambiguous',
            requires_clarification=True,
            candidates=candidates,
            reasoning=f"'{mention}' found in {len(matches)} places"
        )
    
    async def _try_fuzzy_match(self, mention: str,
                               context: QueryContext) -> Optional[ResolutionResult]:
        """Try fuzzy matching for typos and partial matches"""
        
        fuzzy_matches = self.index.fuzzy_search(mention, threshold=0.75)
        
        if not fuzzy_matches:
            return None
        
        # If top match is very close, use it
        if fuzzy_matches[0][1] > 0.9:
            return ResolutionResult(
                match=fuzzy_matches[0][0],
                confidence=fuzzy_matches[0][1],
                source='fuzzy_high',
                requires_clarification=False,
                candidates=[
                    ValueMatch(m, s, 'fuzzy', mention) 
                    for m, s in fuzzy_matches[:3]
                ]
            )
        
        # Return candidates for further processing
        return ResolutionResult(
            match=None,
            confidence=fuzzy_matches[0][1],
            source='fuzzy_candidates',
            requires_clarification=True,
            candidates=[
                ValueMatch(m, s, 'fuzzy', mention) 
                for m, s in fuzzy_matches[:5]
            ]
        )
    
    async def _disambiguate_with_context(self, 
                                          candidates: List[ValueMatch],
                                          context: QueryContext) -> ResolutionResult:
        """Score candidates based on query context"""
        
        scored = []
        
        for match in candidates:
            entry = match.entry
            score = match.score  # Base score from match type
            
            # Intent matching
            if context.intent:
                intent_score = self.intent_analyzer.intent_matches_entity_type(
                    context.intent, entry.entity_type.value
                )
                score += intent_score * 0.2
            
            # Table mentioned in query?
            if entry.table.lower() in context.query.lower():
                score += 0.15
            
            # Frequency (common values are more likely to be queried)
            score += min(entry.frequency / 10000, 0.05)
            
            scored.append((match, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_match, best_score = scored[0]
        
        # Check if clearly best
        if len(scored) > 1:
            score_diff = best_score - scored[1][1]
            if score_diff > 0.2:
                # Clear winner
                return ResolutionResult(
                    match=best_match.entry,
                    confidence=min(best_score, 0.95),
                    source='context_clear_winner',
                    requires_clarification=False,
                    candidates=[m for m, s in scored[:3]],
                    reasoning=f"Clearly best match by {score_diff:.2f} margin"
                )
        
        return ResolutionResult(
            match=best_match.entry,
            confidence=best_score,
            source='context_best_guess',
            requires_clarification=best_score < 0.75,
            candidates=[m for m, s in scored[:3]],
            reasoning=f"Best guess (confidence: {best_score:.2f})"
        )
    
    async def _generate_clarification(self, mention: str,
                                       candidates: List[ValueMatch],
                                       context: QueryContext) -> ResolutionResult:
        """Generate clarification request when ambiguous"""
        
        # Group by entity type
        by_type = {}
        for match in candidates:
            etype = match.entry.entity_type.value
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(match)
        
        if len(by_type) == 2:
            # Simple binary choice
            types = list(by_type.keys())
            question = (
                f"I found '{mention}' in two places. Did you mean:\n"
                f"1. The {types[0]} ({by_type[types[0]][0].entry.table} table)\n"
                f"2. The {types[1]} ({by_type[types[1]][0].entry.table} table)"
            )
        else:
            # Multiple options
            question = f"'{mention}' could refer to:\n"
            for i, match in enumerate(candidates[:3], 1):
                entry = match.entry
                question += f"{i}. {entry.canonical_value} ({entry.table}.{entry.column})\n"
        
        return ResolutionResult(
            match=None,
            confidence=0.0,
            source='needs_clarification',
            requires_clarification=True,
            candidates=candidates[:3],
            clarification_question=question,
            reasoning=f"Ambiguous: {len(candidates)} possible matches"
        )
    
    def _combine_candidates(self, *candidate_lists: List[ValueMatch]) -> List[ValueMatch]:
        """Combine candidates from multiple sources, removing duplicates"""
        seen = set()
        combined = []
        
        for candidates in candidate_lists:
            for match in candidates:
                key = f"{match.entry.table}.{match.entry.column}:{match.entry.canonical_value}"
                if key not in seen:
                    seen.add(key)
                    combined.append(match)
        
        # Sort by score
        combined.sort(key=lambda x: x.score, reverse=True)
        return combined
    
    async def record_resolution(self, user_id: str, mention: str, 
                                query: str, result: ResolutionResult,
                                user_selected: Optional[ValueEntry] = None):
        """Record resolution result for learning"""
        
        if user_selected:
            # User made a selection from clarification
            await self.user_preferences.update(user_id, mention, user_selected, query)
            
            await self.user_preferences.record_clarification(
                user_id, mention, query, user_selected, result.candidates
            )
