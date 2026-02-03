# Automated Value-Level Entity Resolution System
## Implementation Plan v1.0

## Overview
Automated pipeline for onboarding new databases and resolving value-level ambiguities with minimal manual effort.

## Core Principles
1. **Zero-config onboarding** - Scan database, auto-generate mappings
2. **Progressive enhancement** - Start with exact matches, layer on intelligence
3. **Self-improving** - Learn from every user interaction
4. **Abbreviation-aware** - Handle LBG, Lloyds, Lloyds Banking Group as same entity

---

## Phase 1: Automated Database Onboarding (Week 1-2)

### 1.1 Schema Discovery & Analysis

```python
class DatabaseProfiler:
    """Automatically profile new databases"""
    
    async def profile_database(self, connection_string: str) -> DatabaseProfile:
        """
        1. Discover all tables and columns
        2. Identify string columns that likely contain entities
        3. Sample values to understand data patterns
        4. Detect foreign key relationships
        5. Identify primary entity tables (clients, companies, etc.)
        """
        
        profile = DatabaseProfile()
        
        # Get all tables
        tables = await self.get_tables()
        
        for table in tables:
            table_profile = TableProfile(name=table)
            
            # Get column stats
            columns = await self.analyze_columns(table)
            
            for col in columns:
                if col.type in ['VARCHAR', 'TEXT', 'STRING']:
                    # Analyze cardinality
                    distinct_count = await self.count_distinct(table, col.name)
                    total_count = await self.count_total(table)
                    
                    # High cardinality + referenced by FK = likely entity column
                    is_entity_column = (
                        distinct_count > 10 and  # Not enums
                        distinct_count < total_count * 0.8 and  # Not unique IDs
                        await self.is_referenced_by_fk(table, col.name)
                    )
                    
                    if is_entity_column:
                        # Sample top values by frequency
                        sample = await self.sample_values(table, col.name, limit=1000)
                        
                        col_profile = ColumnProfile(
                            name=col.name,
                            type=col.type,
                            distinct_count=distinct_count,
                            sample_values=sample,
                            entity_type=self.infer_entity_type(col.name, sample)
                        )
                        
                        table_profile.entity_columns.append(col_profile)
            
            profile.tables.append(table_profile)
        
        # Auto-detect primary entity tables
        profile.primary_entities = self.identify_primary_entities(profile)
        
        return profile
    
    def infer_entity_type(self, column_name: str, sample_values: List[str]) -> EntityType:
        """Automatically detect what kind of entities are in this column"""
        
        column_lower = column_name.lower()
        
        # Pattern matching on column name
        if any(word in column_lower for word in ['client', 'customer', 'account']):
            return EntityType.CLIENT
        
        if any(word in column_lower for word in ['company', 'org', 'business', 'firm']):
            return EntityType.COMPANY
        
        if any(word in column_lower for word in ['project', 'engagement', 'deal']):
            return EntityType.PROJECT
        
        if any(word in column_lower for word in ['product', 'item', 'sku']):
            return EntityType.PRODUCT
        
        # Pattern matching on values
        if sample_values:
            # Check if values look like company names
            company_indicators = ['inc', 'llc', 'ltd', 'corp', 'limited', 'group', 'co.', 'company']
            if any(indicator in ' '.join(sample_values[:10]).lower() for indicator in company_indicators):
                return EntityType.COMPANY
            
            # Check if values look like person names
            if any(' ' in val and val.split()[0][0].isupper() for val in sample_values[:5]):
                return EntityType.PERSON
        
        return EntityType.UNKNOWN
```

### 1.2 Value Indexing Pipeline

```python
class ValueIndexer:
    """Index all entity values for fast retrieval"""
    
    async def build_index(self, profile: DatabaseProfile) -> ValueIndex:
        """
        Build searchable index of all entity values
        """
        index = ValueIndex()
        
        for table in profile.tables:
            for col in table.entity_columns:
                # Get all distinct values with frequencies
                values = await self.fetch_all_values(table.name, col.name)
                
                for value in values:
                    # Generate all variations
                    variations = self.generate_variations(value.value)
                    
                    entry = ValueEntry(
                        canonical_value=value.value,
                        table=table.name,
                        column=col.name,
                        entity_type=col.entity_type,
                        frequency=value.frequency,
                        variations=variations,
                        relationships=await self.get_relationships(table.name, col.name, value.value)
                    )
                    
                    # Index by all variations
                    for variation in variations:
                        index.add(variation.lower(), entry)
                    
                    # Also index by embedding for semantic search
                    await index.add_embedding(value.value, entry)
        
        return index
    
    def generate_variations(self, value: str) -> List[str]:
        """
        Generate all possible variations of a value:
        - Original: "Lloyds Banking Group"
        - Abbreviated: "LBG", "Lloyds", "Lloyds Bank"
        - Suffix variations: "Lloyds Banking Group Ltd", "Lloyds Banking Group Inc"
        - Case variations: "lloyds banking group"
        - Token variations: "LloydsBankingGroup"
        """
        variations = set()
        
        # Original
        variations.add(value)
        variations.add(value.lower())
        variations.add(value.upper())
        
        # Remove common suffixes
        base_name = self.remove_suffixes(value)
        if base_name != value:
            variations.add(base_name)
            variations.add(base_name.lower())
        
        # Generate acronym
        acronym = self.generate_acronym(value)
        if acronym:
            variations.add(acronym)
            variations.add(acronym.lower())
        
        # Common abbreviations
        abbreviations = self.generate_abbreviations(value)
        variations.update(abbreviations)
        
        # Add common suffixes
        for suffix in ['Inc', 'LLC', 'Ltd', 'Limited', 'Corp', 'Corporation', 'Group', 'Company', 'Co.']:
            variations.add(f"{base_name} {suffix}")
            variations.add(f"{base_name}{suffix}")
        
        # Handle & vs "and"
        if '&' in value:
            variations.add(value.replace('&', 'and'))
        if ' and ' in value.lower():
            variations.add(value.lower().replace(' and ', ' & '))
        
        return list(variations)
    
    SUFFIXES = [
        r'\s+Inc\.?$', r'\s+LLC\.?$', r'\s+Ltd\.?$', r'\s+Limited\.?$',
        r'\s+Corp\.?$', r'\s+Corporation\.?$', r'\s+Group\.?$',
        r'\s+Company\.?$', r'\s+Co\.?$', r'\s+PLC\.?$', r'\s+AG\.?$',
        r'\s+GmbH\.?$', r'\s+BV\.?$', r'\s+S\.A\.?$', r'\s+SpA\.?$',
    ]
    
    def remove_suffixes(self, value: str) -> str:
        """Remove legal suffixes to get base company name"""
        result = value
        for suffix_pattern in self.SUFFIXES:
            result = re.sub(suffix_pattern, '', result, flags=re.IGNORECASE).strip()
        return result
    
    def generate_acronym(self, value: str) -> Optional[str]:
        """
        Generate acronym from value
        "Lloyds Banking Group" → "LBG"
        "International Business Machines" → "IBM"
        """
        words = value.split()
        if len(words) >= 2:
            # Take first letter of each word (except common small words)
            small_words = {'the', 'of', 'and', 'for', 'in', 'on', 'at', 'to', 'a', 'an'}
            letters = [word[0].upper() for word in words if word.lower() not in small_words]
            if len(letters) >= 2:
                return ''.join(letters)
        return None
    
    def generate_abbreviations(self, value: str) -> List[str]:
        """
        Generate common abbreviations
        "Lloyds Banking Group" → ["Lloyds", "Lloyds Bank", "LBG"]
        "International Business Machines" → ["IBM", "Business Machines"]
        """
        abbreviations = []
        words = value.split()
        
        # First word only
        abbreviations.append(words[0])
        
        # First two words
        if len(words) >= 2:
            abbreviations.append(' '.join(words[:2]))
        
        # Last word only (if it's a descriptor like "Group", "Inc")
        if len(words) >= 2 and words[-1].lower() not in ['group', 'inc', 'llc', 'ltd']:
            abbreviations.append(words[-1])
        
        return abbreviations
```

### 1.3 Abbreviation Dictionary Auto-Generation

```python
class AbbreviationLearner:
    """
    Automatically discover abbreviations from the data itself
    """
    
    async def discover_abbreviations(self, index: ValueIndex) -> Dict[str, str]:
        """
        Find patterns where short strings likely refer to longer ones:
        - "LBG" → "Lloyds Banking Group"
        - "IBM" → "International Business Machines"
        """
        abbreviations = {}
        
        # Pattern 1: Short codes (2-5 chars, all caps)
        short_codes = [
            value for value in index.all_values()
            if 2 <= len(value) <= 5 and value.isupper() and value.isalpha()
        ]
        
        for code in short_codes:
            # Find potential expansions
            potential = self.find_potential_expansions(code, index)
            
            for expansion in potential:
                score = self.score_abbreviation_match(code, expansion)
                if score > 0.8:
                    abbreviations[code] = expansion
                    abbreviations[code.lower()] = expansion
        
        # Pattern 2: Common first-word references
        # If many queries mention "Lloyds" and it's part of "Lloyds Banking Group"
        # Learn that "Lloyds" can refer to the full name
        for entry in index.entries:
            words = entry.canonical_value.split()
            if len(words) > 1:
                first_word = words[0]
                if len(first_word) > 3:  # Not "The" or "A"
                    abbreviations[first_word] = entry.canonical_value
                    abbreviations[first_word.lower()] = entry.canonical_value
        
        return abbreviations
    
    def find_potential_expansions(self, code: str, index: ValueIndex) -> List[str]:
        """Find values that could be expanded versions of this code"""
        code_letters = list(code)
        matches = []
        
        for entry in index.entries:
            value = entry.canonical_value
            words = value.split()
            
            # Check if first letters match
            first_letters = [word[0].upper() for word in words if word[0].isalpha()]
            if first_letters == code_letters:
                matches.append(value)
            
            # Check for partial matches (e.g., "LBG" matches "Lloyds Bank Group")
            if len(words) >= len(code_letters):
                partial_match = all(
                    words[i][0].upper() == code_letters[i] 
                    for i in range(len(code_letters))
                )
                if partial_match:
                    matches.append(value)
        
        return matches
```

---

## Phase 2: Resolution Engine (Week 2-3)

### 2.1 Multi-Strategy Resolver

```python
class ValueResolver:
    """
    Resolve entity mentions to specific columns with confidence scoring
    """
    
    def __init__(self, index: ValueIndex, abbreviations: Dict[str, str]):
        self.index = index
        self.abbreviations = abbreviations
        self.user_preferences = UserPreferenceStore()
        
    async def resolve(self, 
                      mention: str, 
                      query: str, 
                      user_id: str,
                      context: QueryContext) -> ResolutionResult:
        """
        Main resolution flow with cascading strategies
        """
        
        # Strategy 1: User preferences (learned from past interactions)
        preference = await self.user_preferences.get(user_id, mention, query)
        if preference and preference.confidence > 0.9:
            return ResolutionResult(
                match=preference.match,
                confidence=preference.confidence,
                source="user_preference",
                requires_clarification=False
            )
        
        # Strategy 2: Exact match (including abbreviations)
        exact_matches = self.index.lookup(mention)
        if not exact_matches:
            # Try abbreviation expansion
            expanded = self.abbreviations.get(mention)
            if expanded:
                exact_matches = self.index.lookup(expanded)
        
        if exact_matches:
            result = await self.handle_exact_matches(exact_matches, query, context)
            if result.confidence > 0.85:
                return result
        
        # Strategy 3: Fuzzy match (typos, partial matches)
        fuzzy_matches = self.index.fuzzy_search(mention, threshold=0.8)
        if fuzzy_matches:
            result = await self.handle_fuzzy_matches(fuzzy_matches, query, context)
            if result.confidence > 0.75:
                return result
        
        # Strategy 4: Semantic match (embeddings)
        semantic_matches = await self.index.semantic_search(mention, top_k=5)
        if semantic_matches and semantic_matches[0].score > 0.85:
            return ResolutionResult(
                match=semantic_matches[0].entry,
                confidence=semantic_matches[0].score,
                source="semantic",
                requires_clarification=False
            )
        
        # Strategy 5: Clarification required
        all_candidates = self.combine_candidates(exact_matches, fuzzy_matches, semantic_matches)
        return await self.generate_clarification(mention, all_candidates, query)
    
    async def handle_exact_matches(self, 
                                   matches: List[ValueEntry], 
                                   query: str,
                                   context: QueryContext) -> ResolutionResult:
        """
        When multiple columns have the same value, use context to disambiguate
        """
        if len(matches) == 1:
            return ResolutionResult(
                match=matches[0],
                confidence=0.95,
                source="exact_single",
                requires_clarification=False
            )
        
        # Multiple matches - score each based on query context
        scored = []
        for match in matches:
            score = 0.7  # Base score for exact match
            
            # Query intent analysis
            intent = self.analyze_query_intent(query)
            
            # Does this table/column align with the intent?
            if self.intent_matches_column(intent, match):
                score += 0.2
            
            # Table mention in query?
            if match.table.lower() in query.lower():
                score += 0.1
            
            # Frequency (more common = more likely)
            score += min(match.frequency / 1000, 0.05)
            
            # Recent usage by this user
            recent_usage = await self.user_preferences.get_recent(user_id, match)
            if recent_usage:
                score += 0.05
            
            scored.append((match, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # If top score is significantly higher, use it
        if scored[0][1] - scored[1][1] > 0.15:
            return ResolutionResult(
                match=scored[0][0],
                confidence=scored[0][1],
                source="exact_context",
                requires_clarification=False
            )
        
        # Too close to call - need clarification
        return ResolutionResult(
            match=None,
            confidence=scored[0][1],
            source="exact_ambiguous",
            requires_clarification=True,
            candidates=[m for m, s in scored[:3]]
        )
```

### 2.2 Query Intent Analysis

```python
class IntentAnalyzer:
    """
    Understand what the user is trying to do to guide disambiguation
    """
    
    INTENT_PATTERNS = {
        'revenue_analysis': [
            r'revenue', r'sales', r'income', r'earnings', r'profit',
            r'how much', r'total.*money', r'made.*money'
        ],
        'engagement_tracking': [
            r'engagement', r'project', r'campaign', r'initiative',
            r'working on', r'status of', r'progress'
        ],
        'client_management': [
            r'client', r'customer', r'account', r'relationship',
            r'contact', r'touchpoint'
        ],
        'performance_review': [
            r'performance', r'metrics', r'kpi', r'how.*doing',
            r'results', r'outcomes'
        ]
    }
    
    def analyze(self, query: str) -> QueryIntent:
        """Extract intent from natural language query"""
        query_lower = query.lower()
        
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            scores[intent] = score / len(patterns)
        
        # Return top intent if clearly dominant
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_intents[0][1] > 0.3 and sorted_intents[0][1] > sorted_intents[1][1] * 1.5:
            return QueryIntent(
                primary=sorted_intents[0][0],
                confidence=sorted_intents[0][1],
                secondary=sorted_intents[1][0] if sorted_intents[1][1] > 0.1 else None
            )
        
        return QueryIntent(primary='unknown', confidence=0.0)
```

---

## Phase 3: Smart Clarification (Week 3-4)

### 3.1 Contextual Clarification Engine

```python
class ClarificationEngine:
    """
    Generate helpful clarification questions when ambiguous
    """
    
    async def generate(self, 
                       mention: str, 
                       candidates: List[ValueEntry],
                       query: str,
                       user_id: str) -> ClarificationRequest:
        """
        Generate a clarification request that helps the user quickly identify
        which entity they mean
        """
        
        # Group candidates by semantic type
        by_type = self.group_by_type(candidates)
        
        if len(by_type) == 2:
            # Simple binary choice
            return self.generate_binary_choice(mention, by_type, query)
        
        # Multiple options - show examples and context
        return self.generate_contextual_choice(mention, candidates, query)
    
    def generate_binary_choice(self, mention: str, by_type: Dict, query: str) -> ClarificationRequest:
        """
        When clear dichotomy exists:
        "Did you mean Acme Corp as a client or as an engagement?"
        """
        types = list(by_type.keys())
        
        # Get representative examples for each
        examples_a = [e for e in by_type[types[0]][:2]]
        examples_b = [e for e in by_type[types[1]][:2]]
        
        return ClarificationRequest(
            type="binary_choice",
            question=f"I found '{mention}' in two places. Which one did you mean?",
            options=[
                {
                    "id": f"{types[0]}:{examples_a[0].table}.{examples_a[0].column}",
                    "label": f"The {types[0]} (in {examples_a[0].table} table)",
                    "examples": [e.canonical_value for e in examples_a],
                    "context": self.get_context_description(types[0], query)
                },
                {
                    "id": f"{types[1]}:{examples_b[0].table}.{examples_b[0].column}",
                    "label": f"The {types[1]} (in {examples_b[0].table} table)",
                    "examples": [e.canonical_value for e in examples_b],
                    "context": self.get_context_description(types[1], query)
                }
            ],
            learn_from_answer=True
        )
    
    def get_context_description(self, entity_type: str, query: str) -> str:
        """Explain why this option might be relevant based on query"""
        if entity_type == 'client' and 'revenue' in query.lower():
            return "This would show revenue from this client"
        elif entity_type == 'engagement' and 'status' in query.lower():
            return "This would show the project status"
        return f"This is a {entity_type}"
```

### 3.2 Learning from Clarifications

```python
class ClarificationLearner:
    """
    Every clarification teaches the system
    """
    
    async def record_clarification(self,
                                   user_id: str,
                                   mention: str,
                                   query: str,
                                   selected_option: str,
                                   context: QueryContext):
        """
        Store what the user selected to improve future predictions
        """
        # Record the specific mapping
        await self.db.clarifications.insert({
            'user_id': user_id,
            'mention': mention.lower(),
            'query_pattern': self.extract_pattern(query),
            'selected_table': selected_option.table,
            'selected_column': selected_option.column,
            'timestamp': datetime.now(),
            'query_intent': context.intent
        })
        
        # Update user preference model
        await self.user_preferences.update(user_id, mention, selected_option)
        
        # If this is a common ambiguity, suggest adding to global dictionary
        if await self.is_common_ambiguity(mention):
            await self.suggest_global_rule(mention, selected_option, context)
    
    async def predict_from_history(self, user_id: str, mention: str, query: str) -> Optional[Prediction]:
        """
        Look at past clarifications to predict current intent
        """
        # Get all past clarifications for this user
        history = await self.db.clarifications.find({
            'user_id': user_id,
            'mention': mention.lower()
        }).sort('timestamp', -1).limit(10)
        
        if not history:
            return None
        
        # If 80%+ of the time they chose the same option, return that
        selections = [h.selected_table for h in history]
        most_common = Counter(selections).most_common(1)[0]
        
        if most_common[1] / len(selections) > 0.8:
            return Prediction(
                table=most_common[0],
                confidence=most_common[1] / len(selections),
                source='user_history'
            )
        
        # Check if query pattern matches past patterns
        current_pattern = self.extract_pattern(query)
        matching_patterns = [h for h in history if h.query_pattern == current_pattern]
        
        if matching_patterns:
            pattern_selections = [h.selected_table for h in matching_patterns]
            pattern_common = Counter(pattern_selections).most_common(1)[0]
            
            return Prediction(
                table=pattern_common[0],
                confidence=pattern_common[1] / len(pattern_selections),
                source='pattern_match'
            )
        
        return None
```

---

## Phase 4: Client Onboarding Automation (Week 4)

### 4.1 One-Command Onboarding

```python
class ClientOnboarding:
    """
    Fully automated onboarding for new clients
    """
    
    async def onboard_client(self, connection_string: str, client_config: ClientConfig):
        """
        Complete onboarding pipeline:
        1. Profile database
        2. Build value index
        3. Discover abbreviations
        4. Validate with sample queries
        5. Generate onboarding report
        """
        
        print(f"🔍 Profiling database for {client_config.name}...")
        profiler = DatabaseProfiler()
        profile = await profiler.profile_database(connection_string)
        
        print(f"📊 Found {len(profile.primary_entities)} primary entity types")
        print(f"   - {len(profile.tables)} tables")
        print(f"   - {sum(len(t.entity_columns) for t in profile.tables)} entity columns")
        
        print("\n🗂️  Building value index...")
        indexer = ValueIndexer()
        index = await indexer.build_index(profile)
        
        print(f"   - Indexed {len(index.entries)} unique values")
        print(f"   - Generated {sum(len(e.variations) for e in index.entries)} variations")
        
        print("\n📖 Discovering abbreviations...")
        learner = AbbreviationLearner()
        abbreviations = await learner.discover_abbreviations(index)
        
        print(f"   - Found {len(abbreviations)} abbreviation patterns")
        for short, long in list(abbreviations.items())[:5]:
            print(f"     • {short} → {long}")
        
        print("\n✅ Validation...")
        validator = OnboardingValidator()
        test_results = await validator.run_tests(index, abbreviations)
        
        print(f"   - {test_results.passed}/{test_results.total} validation tests passed")
        
        # Save everything
        await self.save_onboarding_result(client_config, profile, index, abbreviations)
        
        return OnboardingResult(
            profile=profile,
            index=index,
            abbreviations=abbreviations,
            validation=test_results,
            estimated_accuracy=test_results.estimated_accuracy
        )
```

### 4.2 Validation Suite

```python
class OnboardingValidator:
    """
    Test the system with sample queries to ensure quality
    """
    
    async def run_tests(self, index: ValueIndex, abbreviations: Dict) -> ValidationResult:
        """
        Run automated tests to validate the indexing
        """
        tests = [
            # Test exact matches
            ('revenue for Acme Corp', 'clients', 'name'),
            ('status of Project Alpha', 'engagements', 'name'),
            
            # Test abbreviations
            ('LBG revenue', 'clients', 'name'),  # Should expand LBG
            
            # Test fuzzy matches
            ('Acme Corporaton', 'clients', 'name'),  # Typo
            
            # Test suffix variations
            ('Acme Corp Inc', 'clients', 'name'),  # With suffix
        ]
        
        resolver = ValueResolver(index, abbreviations)
        passed = 0
        
        for query, expected_table, expected_column in tests:
            result = await resolver.resolve(query, '', '')
            if result.match and result.match.table == expected_table:
                passed += 1
        
        return ValidationResult(
            total=len(tests),
            passed=passed,
            estimated_accuracy=passed / len(tests)
        )
```

---

## Phase 5: Maintenance & Monitoring (Ongoing)

### 5.1 Change Detection

```python
class ChangeDetector:
    """
    Detect when database values change and update index
    """
    
    async def detect_changes(self, profile: DatabaseProfile, last_index_time: datetime):
        """
        Find new/modified values since last indexing
        """
        changes = {
            'new_values': [],
            'modified_values': [],
            'deleted_values': []
        }
        
        for table in profile.tables:
            for col in table.entity_columns:
                # Check for new values
                new_values = await self.db.fetch(f"""
                    SELECT {col.name}, created_at 
                    FROM {table.name}
                    WHERE created_at > %s
                """, last_index_time)
                
                changes['new_values'].extend(new_values)
        
        return changes
    
    async def incremental_update(self, changes: Dict):
        """Update index with only changed values"""
        for value in changes['new_values']:
            await self.index.add(value)
```

---

## Implementation Timeline

| Phase | Week | Deliverable |
|-------|------|-------------|
| 1.1 | 1 | Database profiler with auto-entity detection |
| 1.2 | 1-2 | Value indexer with variation generation |
| 1.3 | 2 | Abbreviation auto-discovery |
| 2.1 | 2-3 | Multi-strategy resolver |
| 2.2 | 3 | Intent analyzer |
| 3.1 | 3-4 | Smart clarification engine |
| 3.2 | 4 | Learning system |
| 4.1 | 4 | One-command onboarding |
| 4.2 | 4 | Validation suite |
| 5.1 | Ongoing | Change detection |

## Expected Outcomes

- **Setup time**: 5 minutes per new database (vs. weeks of manual NER training)
- **Coverage**: 95%+ of entity values in typical business databases
- **Accuracy**: 90%+ exact match rate, 75%+ context disambiguation rate
- **Abbreviation handling**: Automatic discovery of 80%+ of common abbreviations
- **Improvement**: 10%+ accuracy improvement per 100 user interactions

## Next Steps

1. Start with Phase 1.1 (Database Profiler)
2. Build on your existing entity_extraction.py
3. Test with your demo database
4. Iterate on clarification UX