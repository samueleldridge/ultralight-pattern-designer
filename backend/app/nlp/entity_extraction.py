"""
Entity Extraction Module

Extracts structured entities from natural language queries including:
- Metrics and measures
- Dimensions and groupings
- Time expressions (relative and absolute)
- Filters and conditions
- Sorting and limiting preferences
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from app.llm_provider import get_llm_provider
from app.prompts.registry import get_prompt, PromptType


class EntityType(Enum):
    METRIC = "metric"
    DIMENSION = "dimension"
    TIME_RANGE = "time_range"
    FILTER = "filter"
    AGGREGATION = "aggregation"
    SORT = "sort"
    LIMIT = "limit"


@dataclass
class ExtractedMetric:
    """A metric extracted from query"""
    name: str
    original_text: str
    matched_column: Optional[str] = None
    aggregation: Optional[str] = None
    alias: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ExtractedDimension:
    """A dimension extracted from query"""
    name: str
    original_text: str
    matched_column: Optional[str] = None
    is_time_based: bool = False
    confidence: float = 0.0


@dataclass
class TimeRange:
    """Time range specification"""
    type: str  # relative, absolute, rolling, period
    description: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    grain: Optional[str] = None  # day, week, month, quarter, year
    confidence: float = 0.0


@dataclass
class FilterCondition:
    """Filter condition"""
    column: Optional[str]
    operator: str
    value: Any
    logic: str = "AND"  # AND, OR
    original_text: str = ""


@dataclass
class ExtractedEntities:
    """All entities extracted from a query"""
    metrics: List[ExtractedMetric] = field(default_factory=list)
    dimensions: List[ExtractedDimension] = field(default_factory=list)
    time_range: Optional[TimeRange] = None
    filters: List[FilterCondition] = field(default_factory=list)
    sort: Optional[Dict] = None
    limit: Optional[int] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metrics": [
                {
                    "name": m.name,
                    "original_text": m.original_text,
                    "matched_column": m.matched_column,
                    "aggregation": m.aggregation,
                    "alias": m.alias,
                    "confidence": m.confidence
                }
                for m in self.metrics
            ],
            "dimensions": [
                {
                    "name": d.name,
                    "original_text": d.original_text,
                    "matched_column": d.matched_column,
                    "is_time_based": d.is_time_based,
                    "confidence": d.confidence
                }
                for d in self.dimensions
            ],
            "time_range": {
                "type": self.time_range.type,
                "description": self.time_range.description,
                "start_date": self.time_range.start_date.isoformat() if self.time_range.start_date else None,
                "end_date": self.time_range.end_date.isoformat() if self.time_range.end_date else None,
                "grain": self.time_range.grain,
                "confidence": self.time_range.confidence
            } if self.time_range else None,
            "filters": [
                {
                    "column": f.column,
                    "operator": f.operator,
                    "value": f.value,
                    "logic": f.logic,
                    "original_text": f.original_text
                }
                for f in self.filters
            ],
            "sort": self.sort,
            "limit": self.limit,
            "confidence": self.confidence
        }


class DateParser:
    """Parse relative and absolute date expressions"""
    
    RELATIVE_PATTERNS = {
        # Today/yesterday
        r'\btoday\b': lambda base: (base, base, 'day'),
        r'\byesterday\b': lambda base: (base - timedelta(days=1), base - timedelta(days=1), 'day'),
        
        # This/last periods
        r'\bthis\s+week\b': lambda base: _this_week(base),
        r'\blast\s+week\b': lambda base: _last_week(base),
        r'\bthis\s+month\b': lambda base: _this_month(base),
        r'\blast\s+month\b': lambda base: _last_month(base),
        r'\bthis\s+quarter\b': lambda base: _this_quarter(base),
        r'\blast\s+quarter\b': lambda base: _last_quarter(base),
        r'\bthis\s+year\b': lambda base: _this_year(base),
        r'\blast\s+year\b': lambda base: _last_year(base),
        
        # Rolling periods
        r'\blast\s+(\d+)\s+days?\b': lambda base, n: (base - timedelta(days=int(n)), base, 'day'),
        r'\blast\s+(\d+)\s+weeks?\b': lambda base, n: (base - timedelta(weeks=int(n)), base, 'week'),
        r'\blast\s+(\d+)\s+months?\b': lambda base, n: _last_n_months(base, int(n)),
        r'\bpast\s+(\d+)\s+days?\b': lambda base, n: (base - timedelta(days=int(n)), base, 'day'),
        r'\bpast\s+(\d+)\s+weeks?\b': lambda base, n: (base - timedelta(weeks=int(n)), base, 'week'),
        r'\bpast\s+(\d+)\s+months?\b': lambda base, n: _last_n_months(base, int(n)),
        
        # Special periods
        r'\bYTD\b|\byear\s+to\s+date\b': lambda base: _ytd(base),
        r'\bMTD\b|\bmonth\s+to\s+date\b': lambda base: _mtd(base),
        r'\bQTD\b|\bquarter\s+to\s+date\b': lambda base: _qtd(base),
        
        # Quarters
        r'\bQ1\b': lambda base: _quarter(base.year, 1),
        r'\bQ2\b': lambda base: _quarter(base.year, 2),
        r'\bQ3\b': lambda base: _quarter(base.year, 3),
        r'\bQ4\b': lambda base: _quarter(base.year, 4),
        r'\blast\s+Q1\b': lambda base: _quarter(base.year - 1, 1),
        r'\blast\s+Q2\b': lambda base: _quarter(base.year - 1, 2),
        r'\blast\s+Q3\b': lambda base: _quarter(base.year - 1, 3),
        r'\blast\s+Q4\b': lambda base: _quarter(base.year - 1, 4),
    }
    
    @classmethod
    def parse(cls, text: str, base_date: Optional[datetime] = None) -> Optional[TimeRange]:
        """Parse a date expression from text"""
        if base_date is None:
            base_date = datetime.utcnow()
        
        text_lower = text.lower()
        
        for pattern, func in cls.RELATIVE_PATTERNS.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                groups = match.groups()
                if groups:
                    start, end, grain = func(base_date, *groups)
                else:
                    start, end, grain = func(base_date)
                
                return TimeRange(
                    type="relative",
                    description=match.group(0),
                    start_date=start,
                    end_date=end,
                    grain=grain,
                    confidence=0.9
                )
        
        # Try absolute date patterns
        return cls._parse_absolute(text, base_date)
    
    @classmethod
    def _parse_absolute(cls, text: str, base_date: datetime) -> Optional[TimeRange]:
        """Parse absolute date ranges like '2024-01-01 to 2024-01-31'"""
        # Pattern: YYYY-MM-DD to YYYY-MM-DD
        pattern = r'(\d{4}-\d{2}-\d{2})\s+(?:to|through|until)\s+(\d{4}-\d{2}-\d{2})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = datetime.strptime(match.group(1), '%Y-%m-%d')
            end = datetime.strptime(match.group(2), '%Y-%m-%d')
            return TimeRange(
                type="absolute",
                description=match.group(0),
                start_date=start,
                end_date=end,
                grain="day",
                confidence=0.95
            )
        
        # Pattern: January 2024, Jan 2024
        month_pattern = r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+(\d{4})\b'
        match = re.search(month_pattern, text, re.IGNORECASE)
        if match:
            month_names = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
                'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
                'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
                'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
            }
            month = month_names.get(match.group(1).lower())
            year = int(match.group(2))
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(days=1)
            
            return TimeRange(
                type="absolute",
                description=match.group(0),
                start_date=start,
                end_date=end,
                grain="month",
                confidence=0.9
            )
        
        return None


# Helper functions for date calculations
def _this_week(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get this week's date range"""
    start = base - timedelta(days=base.weekday())
    end = start + timedelta(days=6)
    return start, end, 'day'

def _last_week(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get last week's date range"""
    start = base - timedelta(days=base.weekday() + 7)
    end = start + timedelta(days=6)
    return start, end, 'day'

def _this_month(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get this month's date range"""
    start = base.replace(day=1)
    if base.month == 12:
        end = base.replace(year=base.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = base.replace(month=base.month + 1, day=1) - timedelta(days=1)
    return start, end, 'day'

def _last_month(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get last month's date range"""
    if base.month == 1:
        start = base.replace(year=base.year - 1, month=12, day=1)
        end = base.replace(year=base.year - 1, month=12, day=31)
    else:
        start = base.replace(month=base.month - 1, day=1)
        end = base.replace(month=base.month, day=1) - timedelta(days=1)
    return start, end, 'day'

def _last_n_months(base: datetime, n: int) -> Tuple[datetime, datetime, str]:
    """Get last n months"""
    year = base.year
    month = base.month - n
    while month <= 0:
        year -= 1
        month += 12
    start = datetime(year, month, 1)
    end = base
    return start, end, 'month'

def _this_quarter(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get this quarter's date range"""
    quarter = (base.month - 1) // 3
    start_month = quarter * 3 + 1
    start = base.replace(month=start_month, day=1)
    if start_month == 10:
        end = base.replace(year=base.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = base.replace(month=start_month + 3, day=1) - timedelta(days=1)
    return start, end, 'day'

def _last_quarter(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get last quarter's date range"""
    quarter = (base.month - 1) // 3
    if quarter == 0:
        start_month = 10
        year = base.year - 1
    else:
        start_month = (quarter - 1) * 3 + 1
        year = base.year
    start = datetime(year, start_month, 1)
    if start_month == 10:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, start_month + 3, 1) - timedelta(days=1)
    return start, end, 'day'

def _this_year(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get this year's date range"""
    start = base.replace(month=1, day=1)
    end = base.replace(month=12, day=31)
    return start, end, 'day'

def _last_year(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get last year's date range"""
    start = base.replace(year=base.year - 1, month=1, day=1)
    end = base.replace(year=base.year - 1, month=12, day=31)
    return start, end, 'day'

def _ytd(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get year to date"""
    start = base.replace(month=1, day=1)
    return start, base, 'day'

def _mtd(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get month to date"""
    start = base.replace(day=1)
    return start, base, 'day'

def _qtd(base: datetime) -> Tuple[datetime, datetime, str]:
    """Get quarter to date"""
    quarter = (base.month - 1) // 3
    start_month = quarter * 3 + 1
    start = base.replace(month=start_month, day=1)
    return start, base, 'day'

def _quarter(year: int, q: int) -> Tuple[datetime, datetime, str]:
    """Get specific quarter"""
    start_month = (q - 1) * 3 + 1
    start = datetime(year, start_month, 1)
    if start_month == 10:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, start_month + 3, 1) - timedelta(days=1)
    return start, end, 'day'


class EntityExtractor:
    """Extract entities from natural language queries"""
    
    COMMON_METRICS = [
        'revenue', 'sales', 'profit', 'income', 'cost', 'expense',
        'users', 'customers', 'orders', 'transactions', 'visits',
        'clicks', 'conversions', 'leads', 'signups', 'downloads',
        'amount', 'count', 'total', 'average', 'avg', 'sum'
    ]
    
    COMMON_AGGREGATIONS = {
        'total': 'SUM',
        'sum': 'SUM',
        'average': 'AVG',
        'avg': 'AVG',
        'mean': 'AVG',
        'count': 'COUNT',
        'number of': 'COUNT',
        'how many': 'COUNT',
        'minimum': 'MIN',
        'min': 'MIN',
        'lowest': 'MIN',
        'maximum': 'MAX',
        'max': 'MAX',
        'highest': 'MAX',
    }
    
    SORT_PATTERNS = {
        r'\btop\s+(\d+)\b': ('DESC', 'limit'),
        r'\bbottom\s+(\d+)\b': ('ASC', 'limit'),
        r'\bhighest\s+(\d+)\b': ('DESC', 'limit'),
        r'\blowest\s+(\d+)\b': ('ASC', 'limit'),
        r'\bordered\s+by\s+(\w+)\s+(asc|ascending)': ('ASC', 'column'),
        r'\bordered\s+by\s+(\w+)\s+(desc|descending)': ('DESC', 'column'),
        r'\bsorted\s+by\s+(\w+)': ('auto', 'column'),
    }
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or get_llm_provider()
    
    async def extract(self, query: str, schema_context: Optional[Dict] = None) -> ExtractedEntities:
        """Extract all entities from a query"""
        
        entities = ExtractedEntities()
        
        # Parse time expressions
        time_range = DateParser.parse(query)
        if time_range:
            entities.time_range = time_range
        
        # Extract metrics using patterns
        entities.metrics = self._extract_metrics(query)
        
        # Extract dimensions
        entities.dimensions = self._extract_dimensions(query)
        
        # Extract filters
        entities.filters = self._extract_filters(query)
        
        # Extract sort and limit
        sort, limit = self._extract_sort_and_limit(query)
        entities.sort = sort
        entities.limit = limit
        
        # Use LLM for enhanced extraction if confidence is low
        if entities.confidence < 0.7:
            llm_entities = await self._extract_with_llm(query, schema_context)
            entities = self._merge_entities(entities, llm_entities)
        
        return entities
    
    def _extract_metrics(self, query: str) -> List[ExtractedMetric]:
        """Extract metrics from query using patterns"""
        metrics = []
        query_lower = query.lower()
        
        for metric_name in self.COMMON_METRICS:
            pattern = rf'\b{metric_name}\w*\b'
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                # Check for aggregation
                aggregation = None
                for agg_word, agg_func in self.COMMON_AGGREGATIONS.items():
                    if agg_word in query_lower[:match.start()]:
                        aggregation = agg_func
                        break
                
                metrics.append(ExtractedMetric(
                    name=metric_name,
                    original_text=match.group(0),
                    aggregation=aggregation,
                    confidence=0.8
                ))
        
        return metrics
    
    def _extract_dimensions(self, query: str) -> List[ExtractedDimension]:
        """Extract dimensions (group by fields) from query"""
        dimensions = []
        query_lower = query.lower()
        
        # Pattern: "by X", "grouped by X", "for each X"
        patterns = [
            r'\bby\s+(\w+(?:\s+\w+)*)',
            r'\bgrouped\s+by\s+(\w+(?:\s+\w+)*)',
            r'\bfor\s+each\s+(\w+)',
            r'\bbreakdown\s+(?:by|of)\s+(\w+(?:\s+\w+)*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                dim_name = match.group(1).strip()
                is_time = any(t in dim_name for t in ['date', 'time', 'day', 'week', 'month', 'year'])
                
                dimensions.append(ExtractedDimension(
                    name=dim_name,
                    original_text=match.group(0),
                    is_time_based=is_time,
                    confidence=0.75
                ))
        
        return dimensions
    
    def _extract_filters(self, query: str) -> List[FilterCondition]:
        """Extract filter conditions from query"""
        filters = []
        query_lower = query.lower()
        
        # Pattern: "where X is Y", "for X", "in Y", "from Z"
        filter_patterns = [
            (r'\bwhere\s+(\w+)\s+(is|equals?|=?|=)\s+["\']?([^"\']+)["\']?', lambda m: (m.group(1), '=', m.group(3))),
            (r'\bfor\s+(\w+)\s*[=:]\s*["\']?([^"\']+)["\']?', lambda m: (m.group(1), '=', m.group(2))),
            (r'\bin\s+["\']?([^"\']+)["\']?', lambda m: (None, 'IN', m.group(1))),
            (r'\bfrom\s+["\']?([^"\']+)["\']?(?:\s+to\s+["\']?([^"\']+)["\']?)?', lambda m: (None, 'RANGE', (m.group(1), m.group(2)))),
        ]
        
        for pattern, extractor in filter_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                column, operator, value = extractor(match)
                filters.append(FilterCondition(
                    column=column,
                    operator=operator,
                    value=value,
                    original_text=match.group(0)
                ))
        
        return filters
    
    def _extract_sort_and_limit(self, query: str) -> Tuple[Optional[Dict], Optional[int]]:
        """Extract sorting and limit preferences"""
        sort = None
        limit = None
        query_lower = query.lower()
        
        for pattern, (direction, ptype) in self.SORT_PATTERNS.items():
            match = re.search(pattern, query_lower)
            if match:
                if ptype == 'limit':
                    limit = int(match.group(1))
                else:
                    sort = {
                        'column': match.group(1),
                        'direction': direction
                    }
        
        return sort, limit
    
    async def _extract_with_llm(self, query: str, schema_context: Optional[Dict] = None) -> ExtractedEntities:
        """Use LLM for entity extraction"""
        
        available_metrics = schema_context.get('metrics', []) if schema_context else []
        available_dimensions = schema_context.get('dimensions', []) if schema_context else []
        
        prompt = get_prompt("entity_extractor", PromptType.ENTITY_EXTRACTION)
        rendered = prompt.render(
            query=query,
            available_metrics=json.dumps(available_metrics),
            available_dimensions=json.dumps(available_dimensions)
        )
        
        try:
            result = await self.llm_provider.generate_json(
                prompt=rendered,
                system_prompt="You are an expert at extracting structured information from text."
            )
            
            return self._parse_llm_result(result)
        except Exception as e:
            # Return empty entities on error
            return ExtractedEntities()
    
    def _parse_llm_result(self, result: Dict) -> ExtractedEntities:
        """Parse LLM extraction result into ExtractedEntities"""
        entities = ExtractedEntities()
        
        # Parse metrics
        for m in result.get('metrics', []):
            entities.metrics.append(ExtractedMetric(
                name=m.get('name', ''),
                original_text=m.get('original_text', ''),
                matched_column=m.get('matched_to'),
                aggregation=m.get('aggregation'),
                alias=m.get('alias'),
                confidence=m.get('confidence', 0.5)
            ))
        
        # Parse dimensions
        for d in result.get('dimensions', []):
            entities.dimensions.append(ExtractedDimension(
                name=d.get('name', ''),
                original_text=d.get('original_text', ''),
                matched_column=d.get('matched_to'),
                is_time_based=d.get('is_time_based', False),
                confidence=d.get('confidence', 0.5)
            ))
        
        # Parse time range
        tr = result.get('time_range')
        if tr:
            entities.time_range = TimeRange(
                type=tr.get('type', 'relative'),
                description=tr.get('description', ''),
                start_date=datetime.fromisoformat(tr['start_date']) if tr.get('start_date') else None,
                end_date=datetime.fromisoformat(tr['end_date']) if tr.get('end_date') else None,
                grain=tr.get('grain'),
                confidence=tr.get('confidence', 0.5)
            )
        
        # Parse filters
        for f in result.get('filters', []):
            entities.filters.append(FilterCondition(
                column=f.get('column'),
                operator=f.get('operator', '='),
                value=f.get('value'),
                logic=f.get('logic', 'AND'),
                original_text=f.get('original_text', '')
            ))
        
        entities.sort = result.get('sort')
        entities.limit = result.get('limit')
        entities.confidence = result.get('confidence', 0.5)
        
        return entities
    
    def _merge_entities(self, pattern_entities: ExtractedEntities, llm_entities: ExtractedEntities) -> ExtractedEntities:
        """Merge entities from pattern matching and LLM extraction"""
        merged = ExtractedEntities()
        
        # Prefer pattern matches for time (more reliable)
        merged.time_range = pattern_entities.time_range or llm_entities.time_range
        
        # Combine metrics, preferring higher confidence
        merged.metrics = pattern_entities.metrics.copy()
        for m in llm_entities.metrics:
            if not any(pm.name == m.name for pm in merged.metrics):
                merged.metrics.append(m)
        
        # Combine dimensions
        merged.dimensions = pattern_entities.dimensions.copy()
        for d in llm_entities.dimensions:
            if not any(pd.name == d.name for pd in merged.dimensions):
                merged.dimensions.append(d)
        
        # Combine filters
        merged.filters = pattern_entities.filters + llm_entities.filters
        
        # Prefer explicit values
        merged.sort = pattern_entities.sort or llm_entities.sort
        merged.limit = pattern_entities.limit or llm_entities.limit
        
        return merged


# Convenience function
async def extract_entities(query: str, schema_context: Optional[Dict] = None) -> ExtractedEntities:
    """Extract entities from a query"""
    extractor = EntityExtractor()
    return await extractor.extract(query, schema_context)
