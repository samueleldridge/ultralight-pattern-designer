"""
Value Indexer Module

Builds searchable index of entity values with automatic variation generation.
Handles abbreviations, suffixes, and fuzzy matching.
"""

import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

from app.entity_resolution.profiler import (
    DatabaseProfile, ColumnProfile, ValueEntry, EntityType
)


class VariationGenerator:
    """Generate all possible variations of entity values"""
    
    # Common company/legal suffixes to strip/add
    SUFFIXES = [
        (r'\s+Inc\.?$', ' Inc.'),
        (r'\s+LLC\.?$', ' LLC'),
        (r'\s+Ltd\.?$', ' Ltd'),
        (r'\s+Limited\.?$', ' Limited'),
        (r'\s+Corp\.?$', ' Corp'),
        (r'\s+Corporation\.?$', ' Corporation'),
        (r'\s+Group\.?$', ' Group'),
        (r'\s+Company\.?$', ' Company'),
        (r'\s+Co\.?$', ' Co'),
        (r'\s+PLC\.?$', ' PLC'),
        (r'\s+AG\.?$', ' AG'),
        (r'\s+GmbH\.?$', ' GmbH'),
        (r'\s+BV\.?$', ' BV'),
        (r'\s+S\.A\.?$', ' S.A'),
        (r'\s+SpA\.?$', ' SpA'),
        (r'\s+LLP\.?$', ' LLP'),
        (r'\s+LP\.?$', ' LP'),
    ]
    
    # Words to skip when generating acronyms
    SKIP_WORDS = {
        'the', 'of', 'and', 'for', 'in', 'on', 'at', 'to', 'a', 'an',
        '&', 'and', 'the', 'a', 'an', 'of', 'for', 'in', 'on'
    }
    
    def generate_variations(self, value: str) -> List[str]:
        """
        Generate all possible variations of a value:
        - Original: "Lloyds Banking Group"
        - Abbreviated: "LBG", "Lloyds", "Lloyds Bank"
        - Suffix variations: "Lloyds Banking Group Ltd"
        - Case variations: "lloyds banking group"
        - Combined: "Lloyds Banking Group Inc"
        """
        if not value or not isinstance(value, str):
            return []
        
        variations = set()
        original = value.strip()
        
        # Original forms
        variations.add(original)
        variations.add(original.lower())
        variations.add(original.upper())
        
        # Remove suffixes to get base name
        base_name = self._remove_suffixes(original)
        if base_name != original:
            variations.add(base_name)
            variations.add(base_name.lower())
            variations.add(base_name.upper())
        
        # Generate acronym
        acronym = self._generate_acronym(original)
        if acronym:
            variations.add(acronym)
            variations.add(acronym.lower())
        
        # Generate acronym from base name
        if base_name != original:
            base_acronym = self._generate_acronym(base_name)
            if base_acronym and base_acronym != acronym:
                variations.add(base_acronym)
                variations.add(base_acronym.lower())
        
        # Generate partial forms
        partials = self._generate_partials(original)
        variations.update(partials)
        
        # Add suffix variations to base name
        suffix_variations = self._add_suffix_variations(base_name)
        variations.update(suffix_variations)
        
        # Handle & vs "and"
        if '&' in original:
            with_and = original.replace('&', 'and')
            variations.add(with_and)
            variations.add(with_and.lower())
        
        if ' and ' in original.lower():
            with_amp = original.lower().replace(' and ', ' & ')
            variations.add(with_amp)
            # Also title case version
            words = original.split()
            title_with_amp = ' '.join(
                w if w.lower() != 'and' else '&' for w in words
            )
            variations.add(title_with_amp)
        
        # Remove extra whitespace
        cleaned_variations = set()
        for v in variations:
            cleaned = ' '.join(v.split())
            if cleaned:
                cleaned_variations.add(cleaned)
        
        return list(cleaned_variations)
    
    def _remove_suffixes(self, value: str) -> str:
        """Remove legal suffixes to get base company name"""
        result = value.strip()
        for pattern, _ in self.SUFFIXES:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
        return result
    
    def _generate_acronym(self, value: str) -> Optional[str]:
        """
        Generate acronym from value
        "Lloyds Banking Group" → "LBG"
        "International Business Machines" → "IBM"
        """
        words = value.split()
        if len(words) < 2:
            return None
        
        # Take first letter of each word (except skip words)
        letters = []
        for word in words:
            clean_word = word.strip('()[]{}.,;:!?')
            if clean_word.lower() not in self.SKIP_WORDS and clean_word:
                letters.append(clean_word[0].upper())
        
        if len(letters) >= 2:
            return ''.join(letters)
        
        return None
    
    def _generate_partials(self, value: str) -> Set[str]:
        """
        Generate partial forms of the name
        "Lloyds Banking Group" → {"Lloyds", "Lloyds Bank", "Banking Group"}
        """
        partials = set()
        words = value.split()
        
        if len(words) >= 2:
            # First word only (if meaningful)
            first = words[0]
            if len(first) > 2:
                partials.add(first)
                partials.add(first.lower())
            
            # First two words
            if len(words) >= 2:
                first_two = ' '.join(words[:2])
                partials.add(first_two)
                partials.add(first_two.lower())
            
            # Last word only (if not a suffix)
            last = words[-1]
            if len(last) > 2 and last.lower() not in ['group', 'inc', 'llc', 'ltd', 'corp']:
                partials.add(last)
                partials.add(last.lower())
            
            # Last two words
            if len(words) >= 2:
                last_two = ' '.join(words[-2:])
                partials.add(last_two)
                partials.add(last_two.lower())
        
        return partials
    
    def _add_suffix_variations(self, base_name: str) -> Set[str]:
        """Add common suffix variations to base name"""
        variations = set()
        
        for _, suffix in self.SUFFIXES:
            # With space
            variations.add(f"{base_name}{suffix}")
            # Without space (e.g., "AcmeInc")
            variations.add(f"{base_name}{suffix.strip()}")
        
        return variations
    
    def normalize(self, value: str) -> str:
        """Normalize a value for comparison"""
        # Lowercase
        normalized = value.lower()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        # Remove common suffixes for comparison
        normalized = self._remove_suffixes(normalized)
        return normalized.strip()


class ValueIndex:
    """In-memory index for fast entity value lookup"""
    
    def __init__(self):
        self.entries: Dict[str, ValueEntry] = {}  # canonical_value -> entry
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)  # variation -> canonical_values
        self.variation_generator = VariationGenerator()
        self.embedding_index: Optional[Any] = None  # For semantic search
    
    def add(self, entry: ValueEntry):
        """Add a value entry to the index"""
        self.entries[entry.canonical_value] = entry
        
        # Index all variations
        for variation in entry.variations:
            self.inverted_index[variation.lower()].append(entry.canonical_value)
    
    def lookup(self, value: str) -> List[ValueEntry]:
        """Exact lookup including variations"""
        value_lower = value.lower().strip()
        
        # Direct lookup
        if value_lower in self.inverted_index:
            canonical_values = self.inverted_index[value_lower]
            return [self.entries[cv] for cv in canonical_values]
        
        return []
    
    def fuzzy_search(self, value: str, threshold: float = 0.8) -> List[Tuple[ValueEntry, float]]:
        """Fuzzy search using Levenshtein distance"""
        from difflib import SequenceMatcher
        
        value_lower = value.lower().strip()
        matches = []
        
        # Check against all indexed variations
        for variation, canonical_values in self.inverted_index.items():
            similarity = SequenceMatcher(None, value_lower, variation).ratio()
            if similarity >= threshold:
                for cv in canonical_values:
                    matches.append((self.entries[cv], similarity))
        
        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        total_entries = len(self.entries)
        total_variations = sum(len(e.variations) for e in self.entries.values())
        
        return {
            'total_entries': total_entries,
            'total_variations': total_variations,
            'avg_variations_per_entry': total_variations / total_entries if total_entries > 0 else 0,
            'index_size_mb': self._estimate_size()
        }
    
    def _estimate_size(self) -> float:
        """Rough estimate of memory usage in MB"""
        # Very rough estimate
        total_chars = sum(
            len(e.canonical_value) + sum(len(v) for v in e.variations)
            for e in self.entries.values()
        )
        return total_chars / (1024 * 1024) * 2  # x2 for Python overhead


class ValueIndexer:
    """Build value index from database profile"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.variation_generator = VariationGenerator()
    
    async def build_index(self, profile: DatabaseProfile) -> ValueIndex:
        """Build complete value index from profile"""
        index = ValueIndex()
        
        print("🔍 Indexing entity values...")
        
        total_values = 0
        for table in profile.tables:
            for col in table.entity_columns:
                print(f"   Indexing {table.name}.{col.name} ({col.distinct_count} values)...")
                
                # Fetch all distinct values
                values = await self._fetch_values(table.name, col.name, col)
                
                for value_data in values:
                    entry = await self._create_entry(value_data, table.name, col)
                    index.add(entry)
                    total_values += 1
                
                print(f"      ✓ Indexed {len(values)} values")
        
        print(f"\n✅ Index complete: {total_values} entries, {len(index.inverted_index)} variations")
        
        return index
    
    async def _fetch_values(self, table: str, column: str, col_profile: ColumnProfile) -> List[Dict]:
        """Fetch all distinct values from a column"""
        # Use frequency distribution if available
        if col_profile.frequency_distribution:
            return [
                {'value': value, 'frequency': freq}
                for value, freq in col_profile.frequency_distribution.items()
            ]
        
        # Otherwise fetch from DB
        result = await self.db.fetch(f"""
            SELECT {column}, COUNT(*) as freq
            FROM {table}
            WHERE {column} IS NOT NULL AND {column} != ''
            GROUP BY {column}
            ORDER BY freq DESC
            LIMIT 10000
        """)
        
        return [{'value': row[0], 'frequency': row[1]} for row in result]
    
    async def _create_entry(self, value_data: Dict, table: str, col: ColumnProfile) -> ValueEntry:
        """Create a ValueEntry with all variations"""
        value = str(value_data['value'])
        frequency = value_data['frequency']
        
        # Generate variations
        variations = self.variation_generator.generate_variations(value)
        
        # Get relationships (foreign keys, etc.)
        relationships = await self._get_relationships(table, col.name, value)
        
        return ValueEntry(
            canonical_value=value,
            table=table,
            column=col.name,
            entity_type=col.entity_type,
            frequency=frequency,
            variations=variations,
            relationships=relationships
        )
    
    async def _get_relationships(self, table: str, column: str, value: str) -> List[Dict]:
        """Get related entities (e.g., client -> engagements)"""
        # This would query foreign key relationships
        # For now, return empty - can be enhanced later
        return []
