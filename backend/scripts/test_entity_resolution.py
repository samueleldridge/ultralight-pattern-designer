#!/usr/bin/env python3
"""
Demo script for Entity Resolution System

Tests the complete pipeline with sample data.
"""

import asyncio
import sqlite3
import aiosqlite
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.entity_resolution import (
    DatabaseProfiler,
    ValueIndexer,
    AbbreviationLearner,
    EntityResolver,
    onboard_database
)


class AsyncSQLiteWrapper:
    """Simple async wrapper for SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
    
    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    async def fetch(self, query: str, *args):
        cursor = await self.conn.execute(query, args)
        rows = await cursor.fetchall()
        return [tuple(row) for row in rows]
    
    async def execute(self, query: str, *args):
        await self.conn.execute(query, args)
        await self.conn.commit()
    
    async def close(self):
        await self.conn.close()


async def create_demo_database():
    """Create a demo database with sample data"""
    
    db_path = "/tmp/entity_resolution_demo.db"
    
    # Remove existing
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create clients table
    cursor.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT
        )
    """)
    
    # Insert sample clients with variations
    clients = [
        (1, "Lloyds Banking Group", "Financial Services"),
        (2, "Lloyds Banking Group Ltd", "Financial Services"),
        (3, "International Business Machines", "Technology"),
        (4, "IBM Corporation", "Technology"),
        (5, "Acme Corporation", "Manufacturing"),
        (6, "Acme Corp Inc", "Manufacturing"),
        (7, "Acme Corp LLC", "Manufacturing"),
        (8, "Microsoft Corporation", "Technology"),
        (9, "Microsoft Corp", "Technology"),
        (10, "Apple Inc", "Technology"),
        (11, "Apple Computer Inc", "Technology"),
    ]
    cursor.executemany("INSERT INTO clients VALUES (?, ?, ?)", clients)
    
    # Create engagements table (projects for clients)
    cursor.execute("""
        CREATE TABLE engagements (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            client_id INTEGER,
            status TEXT
        )
    """)
    
    # Insert sample engagements (some with same names as clients)
    engagements = [
        (1, "Acme Project", 5, "active"),
        (2, "IBM Implementation", 3, "completed"),
        (3, "Lloyds Migration", 1, "active"),
        (4, "Microsoft Partnership", 8, "planning"),
        (5, "Apple Integration", 10, "active"),
    ]
    cursor.executemany("INSERT INTO engagements VALUES (?, ?, ?, ?)", engagements)
    
    conn.commit()
    conn.close()
    
    return db_path


async def test_variation_generator():
    """Test the variation generator"""
    print("\n🧪 Testing Variation Generator")
    print("-" * 50)
    
    from app.entity_resolution.indexer import VariationGenerator
    
    gen = VariationGenerator()
    
    test_values = [
        "Lloyds Banking Group",
        "International Business Machines",
        "Acme Corporation Inc",
        "Microsoft & Co",
    ]
    
    for value in test_values:
        variations = gen.generate_variations(value)
        print(f"\n{value}:")
        print(f"  Variations: {variations[:8]}")
        print(f"  Total: {len(variations)}")


async def test_profiler():
    """Test database profiler"""
    print("\n🧪 Testing Database Profiler")
    print("-" * 50)
    
    db_path = await create_demo_database()
    db = AsyncSQLiteWrapper(db_path)
    await db.connect()
    
    profiler = DatabaseProfiler(db)
    profile = await profiler.profile_database()
    
    print(f"\nProfiled {len(profile.tables)} tables:")
    for table in profile.tables:
        print(f"\n  📁 {table.name} ({table.total_rows} rows)")
        for col in table.entity_columns:
            print(f"    📊 {col.name}: {col.entity_type.value}")
            print(f"       {col.distinct_count} distinct values")
            print(f"       Sample: {col.sample_values[:3]}")
    
    await db.close()
    return profile


async def test_indexer():
    """Test value indexing"""
    print("\n🧪 Testing Value Indexer")
    print("-" * 50)
    
    db_path = await create_demo_database()
    db = AsyncSQLiteWrapper(db_path)
    await db.connect()
    
    # First profile
    profiler = DatabaseProfiler(db)
    profile = await profiler.profile_database()
    
    # Then index
    indexer = ValueIndexer(db)
    index = await indexer.build_index(profile)
    
    stats = index.get_stats()
    print(f"\n📊 Index Statistics:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Total variations: {stats['total_variations']}")
    print(f"   Avg variations/entry: {stats['avg_variations_per_entry']:.1f}")
    
    # Test lookups
    print("\n🔍 Testing Lookups:")
    test_lookups = [
        "Lloyds Banking Group",
        "lloyds banking group",
        "LBG",
        "IBM",
        "Acme Corp",
        "Microsoft",
    ]
    
    for lookup in test_lookups:
        matches = index.lookup(lookup)
        if matches:
            print(f"   ✓ '{lookup}' → {matches[0].canonical_value}")
        else:
            print(f"   ✗ '{lookup}' → No match")
    
    await db.close()
    return index


async def test_abbreviations():
    """Test abbreviation discovery"""
    print("\n🧪 Testing Abbreviation Discovery")
    print("-" * 50)
    
    db_path = await create_demo_database()
    db = AsyncSQLiteWrapper(db_path)
    await db.connect()
    
    # Build index
    profiler = DatabaseProfiler(db)
    profile = await profiler.profile_database()
    indexer = ValueIndexer(db)
    index = await indexer.build_index(profile)
    
    # Discover abbreviations
    learner = AbbreviationLearner()
    abbrevs = await learner.discover_abbreviations(index)
    
    print(f"\n📖 Discovered Abbreviations:")
    seen = set()
    for short, long in abbrevs.items():
        if short not in seen and short.isupper():
            seen.add(short)
            print(f"   • {short} → {long}")
    
    await db.close()
    return abbrevs


async def test_resolver():
    """Test entity resolution"""
    print("\n🧪 Testing Entity Resolver")
    print("-" * 50)
    
    db_path = await create_demo_database()
    db = AsyncSQLiteWrapper(db_path)
    await db.connect()
    
    # Build everything
    profiler = DatabaseProfiler(db)
    profile = await profiler.profile_database()
    indexer = ValueIndexer(db)
    index = await indexer.build_index(profile)
    learner = AbbreviationLearner()
    abbrevs = await learner.discover_abbreviations(index)
    
    # Create resolver
    resolver = EntityResolver(index, learner)
    
    # Test queries
    test_queries = [
        ("LBG", "revenue for LBG"),
        ("IBM", "projects for IBM"),
        ("Acme", "revenue from Acme"),
        ("Acme", "status of Acme"),
        ("Microsoft", "engagement with Microsoft"),
        ("Lloyds", "Lloyds revenue"),
    ]
    
    print("\n🎯 Resolution Results:")
    for mention, query in test_queries:
        result = await resolver.resolve(mention, query)
        
        if result.match:
            print(f"\n   '{mention}' in '{query}':")
            print(f"   ✓ → {result.match.canonical_value}")
            print(f"     Table: {result.match.table}.{result.match.column}")
            print(f"     Confidence: {result.confidence:.2f}")
            print(f"     Source: {result.source}")
        elif result.requires_clarification:
            print(f"\n   '{mention}' in '{query}':")
            print(f"   ⚠️  Ambiguous - needs clarification")
            print(f"     Candidates: {[c.entry.canonical_value for c in result.candidates[:3]]}")
        else:
            print(f"\n   '{mention}' in '{query}':")
            print(f"   ✗ No match")
    
    await db.close()


async def test_full_onboarding():
    """Test complete onboarding flow"""
    print("\n🧪 Testing Full Onboarding")
    print("=" * 50)
    
    db_path = await create_demo_database()
    db = AsyncSQLiteWrapper(db_path)
    await db.connect()
    
    # Run onboarding
    result = await onboard_database(db, "DemoClient")
    
    await db.close()
    return result


async def main():
    """Run all tests"""
    print("=" * 70)
    print("🚀 ENTITY RESOLUTION SYSTEM - DEMO")
    print("=" * 70)
    
    # Run individual component tests
    await test_variation_generator()
    await test_profiler()
    await test_indexer()
    await test_abbreviations()
    await test_resolver()
    
    # Run full onboarding
    result = await test_full_onboarding()
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    
    if result.success:
        print(f"\n🎉 Onboarding succeeded!")
        print(f"   • Entities indexed: {result.stats.get('total_entries', 0)}")
        print(f"   • Variations: {result.stats.get('total_variations', 0)}")
        print(f"   • Validation accuracy: {result.validation_results.get('accuracy', 0):.1%}")
    else:
        print(f"\n❌ Onboarding failed: {result.errors}")


if __name__ == "__main__":
    asyncio.run(main())
