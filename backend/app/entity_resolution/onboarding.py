"""
Onboarding Module

One-command onboarding for new clients/databases
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from app.entity_resolution.profiler import DatabaseProfiler, DatabaseProfile
from app.entity_resolution.indexer import ValueIndexer, ValueIndex
from app.entity_resolution.abbreviations import AbbreviationLearner
from app.entity_resolution.resolver import EntityResolver


@dataclass
class OnboardingResult:
    """Result of onboarding process"""
    success: bool
    profile: Optional[DatabaseProfile]
    index: Optional[ValueIndex]
    abbreviations: Dict[str, str]
    stats: Dict[str, Any]
    validation_results: Dict[str, Any]
    errors: List[str]
    completed_at: datetime


@dataclass
class ValidationTest:
    """Single validation test"""
    name: str
    query: str
    expected_table: str
    expected_column: str
    passed: bool
    actual_result: Optional[str] = None


class OnboardingValidator:
    """Validate the entity resolution system with test queries"""
    
    def __init__(self, resolver: EntityResolver):
        self.resolver = resolver
    
    async def run_tests(self) -> Dict[str, Any]:
        """Run validation test suite"""
        
        tests = [
            # Test exact matches
            ValidationTest(
                name="exact_client",
                query="revenue for Acme Corp",
                expected_table="clients",
                expected_column="name",
                passed=False
            ),
            
            # Test abbreviation expansion
            ValidationTest(
                name="abbreviation",
                query="LBG revenue",
                expected_table="clients",
                expected_column="name",
                passed=False
            ),
            
            # Test fuzzy matching
            ValidationTest(
                name="fuzzy_typo",
                query="Acme Corporaton revenue",
                expected_table="clients",
                expected_column="name",
                passed=False
            ),
            
            # Test suffix handling
            ValidationTest(
                name="suffix_variation",
                query="Acme Corp Inc",
                expected_table="clients",
                expected_column="name",
                passed=False
            ),
            
            # Test context disambiguation
            ValidationTest(
                name="context_disambiguation",
                query="status of Project Alpha",
                expected_table="engagements",
                expected_column="name",
                passed=False
            ),
        ]
        
        results = []
        for test in tests:
            # Extract mention from query
            mention = self._extract_mention(test.query)
            if mention:
                result = await self.resolver.resolve(mention, test.query)
                
                if result.match:
                    test.passed = (
                        result.match.table == test.expected_table and
                        result.match.column == test.expected_column
                    )
                    test.actual_result = f"{result.match.table}.{result.match.column}"
                else:
                    test.passed = False
                    test.actual_result = "No match"
            else:
                test.passed = False
                test.actual_result = "No mention extracted"
            
            results.append(test)
        
        passed = sum(1 for t in results if t.passed)
        
        return {
            'total': len(results),
            'passed': passed,
            'failed': len(results) - passed,
            'accuracy': passed / len(results) if results else 0,
            'tests': [
                {
                    'name': t.name,
                    'query': t.query,
                    'passed': t.passed,
                    'expected': f"{t.expected_table}.{t.expected_column}",
                    'actual': t.actual_result
                }
                for t in results
            ]
        }
    
    def _extract_mention(self, query: str) -> Optional[str]:
        """Extract entity mention from test query"""
        # Simple extraction - look for capitalized phrases
        patterns = [
            r'for\s+([A-Z][a-zA-Z\s]+?)(?:\s+revenue|\s+sales|$)',
            r'of\s+([A-Z][a-zA-Z\s]+?)(?:\s+status|$)',
            r'([A-Z][a-zA-Z\s]+?)(?:\s+revenue|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        
        return None


class ClientOnboarding:
    """Main onboarding orchestrator"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.profiler = DatabaseProfiler(db_connection)
        self.indexer = ValueIndexer(db_connection)
        self.abbreviation_learner = AbbreviationLearner()
        self.result: Optional[OnboardingResult] = None
    
    async def onboard(self, client_name: str) -> OnboardingResult:
        """
        Complete onboarding pipeline
        """
        print(f"\n🚀 Starting onboarding for: {client_name}")
        print("=" * 50)
        
        errors = []
        profile = None
        index = None
        abbreviations = {}
        
        try:
            # Phase 1: Profile database
            print("\n📊 Phase 1: Profiling database...")
            profile = await self.profiler.profile_database()
            print(f"   ✓ Found {len(profile.tables)} tables with entity columns")
            print(f"   ✓ Primary entities: {len(profile.primary_entities)}")
            
            # Phase 2: Build value index
            print("\n🗂️  Phase 2: Building value index...")
            index = await self.indexer.build_index(profile)
            stats = index.get_stats()
            print(f"   ✓ Indexed {stats['total_entries']} entries")
            print(f"   ✓ Generated {stats['total_variations']} variations")
            
            # Phase 3: Discover abbreviations
            print("\n📖 Phase 3: Discovering abbreviations...")
            abbreviations = await self.abbreviation_learner.discover_abbreviations(index)
            print(f"   ✓ Found {len(abbreviations)//2} abbreviation rules")
            
            # Phase 4: Create resolver
            print("\n🎯 Phase 4: Initializing resolver...")
            resolver = EntityResolver(index, self.abbreviation_learner)
            
            # Phase 5: Validate
            print("\n✅ Phase 5: Running validation tests...")
            validator = OnboardingValidator(resolver)
            validation_results = await validator.run_tests()
            
            print(f"   ✓ {validation_results['passed']}/{validation_results['total']} tests passed")
            print(f"   ✓ Estimated accuracy: {validation_results['accuracy']:.1%}")
            
            # Save artifacts
            await self._save_artifacts(client_name, profile, index, abbreviations)
            
            self.result = OnboardingResult(
                success=True,
                profile=profile,
                index=index,
                abbreviations=abbreviations,
                stats=stats,
                validation_results=validation_results,
                errors=errors,
                completed_at=datetime.utcnow()
            )
            
            self._print_summary()
            
            return self.result
            
        except Exception as e:
            errors.append(str(e))
            print(f"\n❌ Error during onboarding: {e}")
            
            return OnboardingResult(
                success=False,
                profile=profile,
                index=index,
                abbreviations=abbreviations,
                stats={},
                validation_results={},
                errors=errors,
                completed_at=datetime.utcnow()
            )
    
    async def _save_artifacts(self, client_name: str, profile: DatabaseProfile,
                              index: ValueIndex, abbreviations: Dict):
        """Save onboarding artifacts for later use"""
        
        # Save abbreviation rules
        abbrevs_path = f"/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/data/{client_name}_abbreviations.json"
        with open(abbrevs_path, 'w') as f:
            json.dump(abbreviations, f, indent=2)
        
        # Save profile summary
        profile_path = f"/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/data/{client_name}_profile.json"
        profile_data = {
            'tables': [
                {
                    'name': t.name,
                    'total_rows': t.total_rows,
                    'entity_columns': [
                        {
                            'name': c.name,
                            'type': c.type,
                            'distinct_count': c.distinct_count,
                            'entity_type': c.entity_type.value,
                            'sample_values': c.sample_values[:5]
                        }
                        for c in t.entity_columns
                    ]
                }
                for t in profile.tables
            ],
            'primary_entities': profile.primary_entities,
            'indexed_at': profile.indexed_at.isoformat() if profile.indexed_at else None
        }
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        print(f"\n💾 Saved artifacts to data/{client_name}_*.json")
    
    def _print_summary(self):
        """Print onboarding summary"""
        if not self.result:
            return
        
        print("\n" + "=" * 50)
        print("📋 ONBOARDING SUMMARY")
        print("=" * 50)
        
        print(f"\n✅ Status: {'SUCCESS' if self.result.success else 'FAILED'}")
        
        if self.result.stats:
            print(f"\n📊 Index Statistics:")
            print(f"   • Total entries: {self.result.stats['total_entries']:,}")
            print(f"   • Total variations: {self.result.stats['total_variations']:,}")
            print(f"   • Avg variations/entry: {self.result.stats['avg_variations_per_entry']:.1f}")
            print(f"   • Index size: ~{self.result.stats['index_size_mb']:.1f} MB")
        
        if self.result.validation_results:
            vr = self.result.validation_results
            print(f"\n✅ Validation Results:")
            print(f"   • Tests passed: {vr['passed']}/{vr['total']}")
            print(f"   • Accuracy: {vr['accuracy']:.1%}")
            
            if vr.get('tests'):
                print(f"\n   Test Details:")
                for test in vr['tests']:
                    status = "✓" if test['passed'] else "✗"
                    print(f"   {status} {test['name']}: {test['query']}")
        
        if self.result.abbreviations:
            print(f"\n📖 Sample Abbreviations:")
            for short, long in list(self.result.abbreviations.items())[:5]:
                if short.isupper():
                    print(f"   • {short} → {long}")
        
        print("\n" + "=" * 50)
        print("🎉 Onboarding complete! System ready for queries.")
        print("=" * 50)


# Convenience function for one-command onboarding
async def onboard_database(db_connection, client_name: str) -> OnboardingResult:
    """
    One-command database onboarding
    
    Usage:
        result = await onboard_database(db, "AcmeCorp")
    """
    onboarding = ClientOnboarding(db_connection)
    return await onboarding.onboard(client_name)
