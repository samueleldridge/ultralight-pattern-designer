"""
Abbreviation Learning Module

Automatically discovers abbreviations from database values and query patterns.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

from app.entity_resolution.indexer import ValueIndex


@dataclass
class AbbreviationRule:
    """A discovered abbreviation rule"""
    short_form: str
    long_form: str
    confidence: float
    source: str  # 'acronym', 'first_word', 'pattern', 'learned'
    examples: List[str] = None


class AbbreviationLearner:
    """Discover and manage abbreviations"""
    
    def __init__(self):
        self.rules: Dict[str, AbbreviationRule] = {}
        self.pattern_cache: Dict[str, List[str]] = {}
    
    async def discover_abbreviations(self, index: ValueIndex) -> Dict[str, str]:
        """
        Discover abbreviation patterns from indexed values
        Returns: mapping of short_form -> long_form
        """
        print("📖 Discovering abbreviations...")
        
        abbreviations = {}
        
        # Strategy 1: Find short codes that match acronym patterns
        acronym_rules = self._discover_acronyms(index)
        for rule in acronym_rules:
            abbreviations[rule.short_form] = rule.long_form
            abbreviations[rule.short_form.lower()] = rule.long_form
            self.rules[rule.short_form] = rule
        
        print(f"   Found {len(acronym_rules)} acronym patterns")
        
        # Strategy 2: First-word references
        first_word_rules = self._discover_first_word_abbreviations(index)
        for rule in first_word_rules:
            if rule.short_form not in abbreviations:
                abbreviations[rule.short_form] = rule.long_form
                abbreviations[rule.short_form.lower()] = rule.long_form
                self.rules[rule.short_form] = rule
        
        print(f"   Found {len(first_word_rules)} first-word patterns")
        
        # Strategy 3: Common word pattern matching
        pattern_rules = self._discover_pattern_abbreviations(index)
        for rule in pattern_rules:
            if rule.short_form not in abbreviations:
                abbreviations[rule.short_form] = rule.long_form
                self.rules[rule.short_form] = rule
        
        print(f"   Found {len(pattern_rules)} pattern matches")
        
        print(f"✅ Total abbreviations discovered: {len(abbreviations)//2}")
        
        return abbreviations
    
    def _discover_acronyms(self, index: ValueIndex) -> List[AbbreviationRule]:
        """
        Find acronyms like "LBG" -> "Lloyds Banking Group"
        """
        rules = []
        
        # Find short codes (2-5 chars, all caps, all alpha)
        short_codes = [
            variation for variation in index.inverted_index.keys()
            if (2 <= len(variation) <= 5 
                and variation.isupper() 
                and variation.isalpha()
                and not self._is_common_word(variation))
        ]
        
        for code in short_codes:
            code_letters = list(code)
            potential_expansions = []
            
            # Search for values that could be expansions of this code
            for canonical_value, entry in index.entries.items():
                words = canonical_value.split()
                
                if len(words) < len(code_letters):
                    continue
                
                # Check if first letters match
                first_letters = []
                for word in words:
                    clean = word.strip('()[]{}.,;:!?')
                    if clean and clean[0].isalpha():
                        first_letters.append(clean[0].upper())
                
                # Exact acronym match
                if first_letters == code_letters:
                    potential_expansions.append((canonical_value, 1.0))
                
                # Partial match (e.g., "LBG" matches "Lloyds Bank Group")
                elif len(words) >= len(code_letters):
                    partial_match = all(
                        words[i][0].upper() == code_letters[i]
                        for i in range(len(code_letters))
                        if words[i][0].isalpha()
                    )
                    if partial_match:
                        potential_expansions.append((canonical_value, 0.9))
            
            # If we found expansions, create rules
            if potential_expansions:
                # Sort by confidence
                potential_expansions.sort(key=lambda x: x[1], reverse=True)
                best_expansion, confidence = potential_expansions[0]
                
                # Only add if confidence is high enough
                if confidence > 0.8:
                    rule = AbbreviationRule(
                        short_form=code,
                        long_form=best_expansion,
                        confidence=confidence,
                        source='acronym',
                        examples=[e[0] for e in potential_expansions[:3]]
                    )
                    rules.append(rule)
        
        return rules
    
    def _discover_first_word_abbreviations(self, index: ValueIndex) -> List[AbbreviationRule]:
        """
        Discover that first word often refers to full name
        "Lloyds" -> "Lloyds Banking Group"
        """
        rules = []
        
        # Count how many values share the same first word
        first_word_counts = defaultdict(list)
        
        for canonical_value in index.entries.keys():
            words = canonical_value.split()
            if len(words) > 1:
                first_word = words[0]
                if len(first_word) > 3:  # Not "The" or "A"
                    first_word_counts[first_word].append(canonical_value)
        
        # For first words that appear multiple times, create rules
        for first_word, full_names in first_word_counts.items():
            if len(full_names) >= 2:
                # Pick the most common full name
                best_match = full_names[0]
                
                # Check if this first word is also indexed separately
                if first_word.lower() in index.inverted_index:
                    # It's ambiguous - lower confidence
                    confidence = 0.7
                else:
                    # First word only appears as part of longer names
                    confidence = 0.85
                
                rule = AbbreviationRule(
                    short_form=first_word,
                    long_form=best_match,
                    confidence=confidence,
                    source='first_word',
                    examples=full_names[:3]
                )
                rules.append(rule)
        
        return rules
    
    def _discover_pattern_abbreviations(self, index: ValueIndex) -> List[AbbreviationRule]:
        """
        Find common patterns like:
        - "IBM" and "International Business Machines" appearing together
        - "UK" and "United Kingdom"
        """
        rules = []
        
        # Known pattern mappings
        known_patterns = {
            'US': ['United States', 'USA', 'United States of America'],
            'UK': ['United Kingdom', 'Great Britain', 'GB'],
            'EU': ['European Union'],
            'NY': ['New York'],
            'SF': ['San Francisco'],
            'LA': ['Los Angeles'],
        }
        
        for short, long_forms in known_patterns.items():
            for long_form in long_forms:
                if long_form.lower() in index.inverted_index:
                    rule = AbbreviationRule(
                        short_form=short,
                        long_form=long_form,
                        confidence=0.95,
                        source='pattern',
                        examples=[long_form]
                    )
                    rules.append(rule)
                    break
        
        return rules
    
    def _is_common_word(self, word: str) -> bool:
        """Check if a word is common English (not likely an acronym)"""
        common_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'ANY',
            'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET',
            'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD',
            'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'DID', 'SHE', 'USE', 'HER',
            'MAN', 'MEN', 'RUN', 'SUN', 'TOO', 'TOP', 'TRY', 'US', 'YES',
            'YET', 'ACT', 'ADD', 'AGE', 'AGO', 'AID', 'AIR', 'ALL', 'ART',
            'ASK', 'BAD', 'BIG', 'BIT', 'BUS', 'BUY', 'CAR', 'CAT', 'CEO',
            'CFO', 'CIO', 'COO', 'CTO', 'CFO', 'CPA', 'MBA', 'PHD', 'MD',
            'JR', 'SR', 'III', 'IV', 'II', 'MR', 'MRS', 'MS', 'DR'
        }
        return word.upper() in common_words
    
    def expand(self, abbreviation: str) -> Optional[str]:
        """Expand an abbreviation to its full form"""
        if abbreviation in self.rules:
            return self.rules[abbreviation].long_form
        if abbreviation.lower() in self.rules:
            return self.rules[abbreviation.lower()].long_form
        return None
    
    def get_confidence(self, abbreviation: str) -> float:
        """Get confidence score for an abbreviation"""
        if abbreviation in self.rules:
            return self.rules[abbreviation].confidence
        if abbreviation.lower() in self.rules:
            return self.rules[abbreviation.lower()].confidence
        return 0.0
    
    def add_manual_rule(self, short_form: str, long_form: str, confidence: float = 1.0):
        """Add a manually defined abbreviation rule"""
        rule = AbbreviationRule(
            short_form=short_form,
            long_form=long_form,
            confidence=confidence,
            source='manual',
            examples=[long_form]
        )
        self.rules[short_form] = rule
        self.rules[short_form.lower()] = rule
    
    def to_dict(self) -> Dict:
        """Serialize rules to dictionary"""
        return {
            short_form: {
                'long_form': rule.long_form,
                'confidence': rule.confidence,
                'source': rule.source,
                'examples': rule.examples
            }
            for short_form, rule in self.rules.items()
        }
    
    def from_dict(self, data: Dict):
        """Load rules from dictionary"""
        for short_form, rule_data in data.items():
            rule = AbbreviationRule(
                short_form=short_form,
                long_form=rule_data['long_form'],
                confidence=rule_data['confidence'],
                source=rule_data['source'],
                examples=rule_data.get('examples', [])
            )
            self.rules[short_form] = rule
