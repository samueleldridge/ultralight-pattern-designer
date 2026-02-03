"""
Entity Resolution System

Automated value-level entity resolution for natural language to SQL.
Handles abbreviations, synonyms, and ambiguous entity mentions.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import json
from collections import defaultdict, Counter
import asyncio


class EntityType(Enum):
    CLIENT = "client"
    COMPANY = "company"
    PROJECT = "project"
    PRODUCT = "product"
    PERSON = "person"
    LOCATION = "location"
    DEPARTMENT = "department"
    UNKNOWN = "unknown"


@dataclass
class ColumnProfile:
    name: str
    type: str
    distinct_count: int
    sample_values: List[str]
    entity_type: EntityType
    frequency_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class TableProfile:
    name: str
    entity_columns: List[ColumnProfile] = field(default_factory=list)
    total_rows: int = 0


@dataclass
class DatabaseProfile:
    tables: List[TableProfile] = field(default_factory=list)
    primary_entities: List[Tuple[str, str]] = field(default_factory=list)  # (table, column)
    indexed_at: Optional[datetime] = None


@dataclass
class ValueEntry:
    """A single entity value with all its metadata"""
    canonical_value: str
    table: str
    column: str
    entity_type: EntityType
    frequency: int
    variations: List[str] = field(default_factory=list)
    relationships: List[Dict] = field(default_factory=list)
    
    def get_all_forms(self) -> Set[str]:
        """Return all possible forms of this value"""
        forms = {self.canonical_value, self.canonical_value.lower()}
        forms.update(self.variations)
        return forms


@dataclass
class ValueMatch:
    """A match result from the resolver"""
    entry: ValueEntry
    score: float
    match_type: str  # exact, fuzzy, semantic, abbreviation
    matched_form: str  # The actual form that matched


@dataclass
class ResolutionResult:
    """Final resolution result"""
    match: Optional[ValueEntry]
    confidence: float
    source: str
    requires_clarification: bool
    candidates: List[ValueMatch] = field(default_factory=list)
    clarification_question: Optional[str] = None


class DatabaseProfiler:
    """Automatically profile database to discover entity columns"""
    
    # Column name patterns that indicate entity types
    ENTITY_PATTERNS = {
        EntityType.CLIENT: [
            'client', 'customer', 'account', 'buyer', 'purchaser',
            'client_name', 'customer_name', 'account_name'
        ],
        EntityType.COMPANY: [
            'company', 'organization', 'org', 'business', 'firm',
            'enterprise', 'vendor', 'supplier', 'partner',
            'company_name', 'org_name', 'business_name'
        ],
        EntityType.PROJECT: [
            'project', 'engagement', 'campaign', 'initiative',
            'program', 'assignment', 'job', 'deal',
            'project_name', 'engagement_name', 'campaign_name'
        ],
        EntityType.PRODUCT: [
            'product', 'item', 'sku', 'service', 'offering',
            'goods', 'merchandise', 'product_name', 'item_name'
        ],
        EntityType.PERSON: [
            'person', 'user', 'employee', 'contact', 'rep',
            'sales_rep', 'account_manager', 'owner', 'lead',
            'first_name', 'last_name', 'full_name', 'person_name'
        ],
        EntityType.LOCATION: [
            'location', 'region', 'territory', 'country', 'city',
            'state', 'province', 'area', 'zone', 'market'
        ],
        EntityType.DEPARTMENT: [
            'department', 'team', 'division', 'unit', 'group',
            'function', 'sector', 'department_name'
        ]
    }
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def profile_database(self) -> DatabaseProfile:
        """Main profiling entry point"""
        profile = DatabaseProfile()
        
        # Get all tables
        tables = await self._get_tables()
        print(f"📊 Found {len(tables)} tables")
        
        for table_name in tables:
            table_profile = await self._profile_table(table_name)
            if table_profile.entity_columns:
                profile.tables.append(table_profile)
                print(f"   ✓ {table_name}: {len(table_profile.entity_columns)} entity columns")
        
        # Identify primary entity tables
        profile.primary_entities = self._identify_primary_entities(profile)
        profile.indexed_at = datetime.utcnow()
        
        return profile
    
    async def _get_tables(self) -> List[str]:
        """Get list of all tables in database"""
        # SQLite
        result = await self.db.fetch(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in result]
    
    async def _profile_table(self, table_name: str) -> TableProfile:
        """Profile a single table"""
        profile = TableProfile(name=table_name)
        
        # Get total row count
        count_result = await self.db.fetch(f"SELECT COUNT(*) FROM {table_name}")
        profile.total_rows = count_result[0][0]
        
        # Get column info
        columns = await self._get_columns(table_name)
        
        for col_name, col_type in columns:
            # Only analyze string columns (SQLite uses TEXT, PostgreSQL uses VARCHAR/CHAR)
            if any(t in col_type.upper() for t in ['VARCHAR', 'TEXT', 'STRING', 'CHAR']):
                col_profile = await self._analyze_column(table_name, col_name, col_type)
                if col_profile:
                    profile.entity_columns.append(col_profile)
        
        return profile
    
    async def _get_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """Get column names and types for a table"""
        # SQLite
        result = await self.db.fetch(f"PRAGMA table_info({table_name})")
        return [(row[1], row[2]) for row in result]
    
    async def _analyze_column(self, table_name: str, col_name: str, col_type: str) -> Optional[ColumnProfile]:
        """Analyze a single column to determine if it's an entity column"""
        
        # Get distinct count
        distinct_result = await self.db.fetch(
            f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name} WHERE {col_name} IS NOT NULL"
        )
        distinct_count = distinct_result[0][0]
        
        # Skip if too few or too many distinct values
        total_result = await self.db.fetch(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = total_result[0][0]
        
        # Heuristics for entity columns:
        # - More than 3 distinct values (not an enum)
        # - For large tables (>100 rows): less than 90% of total rows (not unique IDs)
        # - For small tables: allow up to 100% distinct (common with company names)
        # - Less than 10,000 distinct (indexable)
        if distinct_count < 3:
            return None
        
        # Only filter as "unique ID" if it's clearly a primary key
        # For small tables or obviously-named columns, be more lenient
        is_likely_pk = (
            col_name.lower() in ['id', 'uuid', 'guid', 'pk'] or
            (total_rows > 100 and distinct_count > total_rows * 0.9)
        )
        if is_likely_pk:
            return None
        
        if distinct_count > 10000:
            # Still might be useful, but log warning
            print(f"   ⚠️  {table_name}.{col_name}: {distinct_count} values (large)")
        
        # Sample top values by frequency
        sample_result = await self.db.fetch(f"""
            SELECT {col_name}, COUNT(*) as freq
            FROM {table_name}
            WHERE {col_name} IS NOT NULL
            GROUP BY {col_name}
            ORDER BY freq DESC
            LIMIT 100
        """)
        
        sample_values = [row[0] for row in sample_result if row[0]]
        frequency_distribution = {row[0]: row[1] for row in sample_result if row[0]}
        
        # Infer entity type
        entity_type = self._infer_entity_type(col_name, sample_values)
        
        return ColumnProfile(
            name=col_name,
            type=col_type,
            distinct_count=distinct_count,
            sample_values=sample_values,
            entity_type=entity_type,
            frequency_distribution=frequency_distribution
        )
    
    def _infer_entity_type(self, column_name: str, sample_values: List[str]) -> EntityType:
        """Infer what type of entities are in this column"""
        
        col_lower = column_name.lower()
        
        # Check column name patterns
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            if any(pattern in col_lower for pattern in patterns):
                return entity_type
        
        # Analyze sample values if available
        if sample_values:
            combined = ' '.join(str(v) for v in sample_values[:20]).lower()
            
            # Check for company indicators
            company_indicators = [
                'inc', 'llc', 'ltd', 'limited', 'corp', 'corporation',
                'group', 'company', 'co.', 'plc', 'ag', 'gmbh', 'bv', 's.a', 'spa'
            ]
            if any(ind in combined for ind in company_indicators):
                return EntityType.COMPANY
            
            # Check for person name patterns (Two capitalized words)
            name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
            if re.search(name_pattern, combined):
                return EntityType.PERSON
        
        return EntityType.UNKNOWN
    
    def _identify_primary_entities(self, profile: DatabaseProfile) -> List[Tuple[str, str]]:
        """Identify the primary entity tables (clients, companies, etc.)"""
        primary = []
        
        for table in profile.tables:
            for col in table.entity_columns:
                # Primary entities have high cardinality and specific types
                if col.entity_type in [EntityType.CLIENT, EntityType.COMPANY]:
                    if col.distinct_count > 10:
                        primary.append((table.name, col.name))
        
        return primary
