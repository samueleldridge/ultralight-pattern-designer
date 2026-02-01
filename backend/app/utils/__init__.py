"""
Shared utility functions used across the backend.
All common functionality should be defined here to avoid duplication.
"""

import re
import hashlib
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


def generate_id(*parts: str) -> str:
    """Generate deterministic ID from parts"""
    content = ":".join(parts)
    return hashlib.md5(content.encode()).hexdigest()


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize a string for safe storage"""
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    # Truncate
    return sanitized[:max_length]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_sql_for_display(sql: str, max_lines: int = 10) -> str:
    """Format SQL for display in UI"""
    lines = sql.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("-- ... (truncated)")
    return '\n'.join(lines)


def estimate_tokens(text: str) -> int:
    """Rough token estimation for text"""
    # Very rough estimate: ~1.3 tokens per word
    return int(len(text.split()) * 1.3)


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def filter_none_values(data: Dict) -> Dict:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats"""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime for display"""
    return dt.strftime(format_str)


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON with fallback"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """Safely dump to JSON with fallback"""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return default


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate_list(items: List) -> List:
    """Remove duplicates while preserving order"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', camel_str).lower()


def mask_sensitive_data(data: Dict, sensitive_keys: List[str]) -> Dict:
    """Mask sensitive values in dictionary"""
    masked = {}
    for key, value in data.items():
        if key in sensitive_keys and isinstance(value, str):
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked[key] = value
    return masked


# SQL-related utilities
def is_read_only_query(sql: str) -> bool:
    """Check if SQL query is read-only"""
    forbidden_keywords = [
        'insert', 'update', 'delete', 'drop', 'truncate',
        'create', 'alter', 'grant', 'revoke'
    ]
    
    sql_lower = sql.lower()
    return not any(kw in sql_lower for kw in forbidden_keywords)


def extract_table_names(sql: str) -> List[str]:
    """Extract table names from SQL query"""
    # Simple regex extraction - for production use proper SQL parser
    pattern = r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = []
    for match in matches:
        tables.extend([m for m in match if m])
    return list(set(tables))


def add_query_limit(sql: str, limit: int) -> str:
    """Add LIMIT clause to query if not present"""
    if 'limit' in sql.lower():
        return sql
    return f"{sql} LIMIT {limit}"


# Validation utilities
def validate_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format"""
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str, re.IGNORECASE))
