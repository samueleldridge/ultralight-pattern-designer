"""
SQL injection prevention and query security.
Comprehensive SQL validation and sanitization.
"""

import re
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from dataclasses import dataclass


class SQLInjectionRisk(Enum):
    """Risk levels for SQL injection detection"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityCheckResult:
    """Result of security check"""
    passed: bool
    risk_level: SQLInjectionRisk
    issues: List[Dict[str, Any]]
    sanitized_query: Optional[str] = None


class SQLInjectionDetector:
    """
    Detect and prevent SQL injection attacks.
    Uses multiple detection strategies.
    """
    
    # Dangerous SQL keywords and patterns
    DANGEROUS_PATTERNS = {
        "comment_out": [
            r'--\s*$',  # Trailing comment
            r'/\*.*\*/',  # Block comment
            r';\s*--',  # Statement end followed by comment
        ],
        "union_attack": [
            r'UNION\s+(ALL\s+)?SELECT',
            r'UNION\s+(ALL\s+)?SELECT\s+NULL',
        ],
        "stacked_queries": [
            r';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)',
        ],
        "boolean_blind": [
            r'OR\s+\'\d+\'=\'\d+\'',
            r'OR\s+\d+=\d+',
            r'AND\s+\d+=\d+',
            r'OR\s*\'[a-zA-Z]+\'=\'[a-zA-Z]+\'',
        ],
        "time_based_blind": [
            r'(WAITFOR|WAIT\s+FOR|DELAY|SLEEP)\s*\(',
            r'BENCHMARK\s*\(',
            r'pg_sleep\s*\(',
        ],
        "error_based": [
            r'CONVERT\s*\(',
            r'CAST\s*\(.*AS\s+INT',
            r'1/0',
        ],
        "out_of_band": [
            r'LOAD_FILE\s*\(',
            r'INTO\s+OUTFILE',
            r'INTO\s+DUMPFILE',
        ],
        "privileged_commands": [
            r'\bGRANT\s+',
            r'\bREVOKE\s+',
            r'\bALTER\s+USER\b',
            r'\bCREATE\s+USER\b',
            r'\bDROP\s+USER\b',
        ]
    }
    
    # Allowlist for safe characters in identifiers
    SAFE_IDENTIFIER_CHARS = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for performance"""
        compiled = {}
        for category, patterns in self.DANGEROUS_PATTERNS.items():
            compiled[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        return compiled
    
    def analyze(self, sql: str) -> SecurityCheckResult:
        """
        Analyze SQL for injection risks.
        Returns detailed security report.
        """
        issues = []
        max_risk = SQLInjectionRisk.NONE
        
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(sql)
                if matches:
                    risk = self._categorize_risk(category)
                    if self._risk_value(risk) > self._risk_value(max_risk):
                        max_risk = risk
                    
                    issues.append({
                        "category": category,
                        "risk": risk.value,
                        "pattern": pattern.pattern[:50],
                        "matches": matches[:3]  # Limit matches reported
                    })
        
        # Check for suspicious string concatenation
        concat_issues = self._check_concatenation(sql)
        if concat_issues:
            issues.extend(concat_issues)
            max_risk = SQLInjectionRisk.HIGH
        
        # Check for hex/char encoding
        encoding_issues = self._check_encoding(sql)
        if encoding_issues:
            issues.extend(encoding_issues)
            max_risk = SQLInjectionRisk.HIGH
        
        return SecurityCheckResult(
            passed=len(issues) == 0,
            risk_level=max_risk,
            issues=issues,
            sanitized_query=None
        )
    
    def _categorize_risk(self, category: str) -> SQLInjectionRisk:
        """Map detection category to risk level"""
        risk_map = {
            "comment_out": SQLInjectionRisk.MEDIUM,
            "union_attack": SQLInjectionRisk.CRITICAL,
            "stacked_queries": SQLInjectionRisk.CRITICAL,
            "boolean_blind": SQLInjectionRisk.HIGH,
            "time_based_blind": SQLInjectionRisk.HIGH,
            "error_based": SQLInjectionRisk.MEDIUM,
            "out_of_band": SQLInjectionRisk.CRITICAL,
            "privileged_commands": SQLInjectionRisk.CRITICAL,
        }
        return risk_map.get(category, SQLInjectionRisk.LOW)
    
    def _risk_value(self, risk: SQLInjectionRisk) -> int:
        """Get numeric value for risk comparison"""
        values = {
            SQLInjectionRisk.NONE: 0,
            SQLInjectionRisk.LOW: 1,
            SQLInjectionRisk.MEDIUM: 2,
            SQLInjectionRisk.HIGH: 3,
            SQLInjectionRisk.CRITICAL: 4
        }
        return values.get(risk, 0)
    
    def _check_concatenation(self, sql: str) -> List[Dict]:
        """Check for dangerous string concatenation patterns"""
        issues = []
        
        # Check for SQL concatenation operators
        concat_pattern = re.compile(
            r'["\']\s*\+\s*["\']|\|\||CONCAT\s*\(',
            re.IGNORECASE
        )
        
        if concat_pattern.search(sql):
            issues.append({
                "category": "concatenation",
                "risk": SQLInjectionRisk.HIGH.value,
                "message": "Potential SQL concatenation detected"
            })
        
        return issues
    
    def _check_encoding(self, sql: str) -> List[Dict]:
        """Check for hex/char encoding patterns"""
        issues = []
        
        # Hex encoding
        hex_pattern = re.compile(r'0x[0-9a-fA-F]{10,}')
        if hex_pattern.search(sql):
            issues.append({
                "category": "hex_encoding",
                "risk": SQLInjectionRisk.HIGH.value,
                "message": "Hex-encoded content detected"
            })
        
        # CHAR() function encoding
        char_pattern = re.compile(r'CHAR\s*\(\s*\d+\s*(,\s*\d+\s*)*\)')
        if char_pattern.search(sql):
            issues.append({
                "category": "char_encoding",
                "risk": SQLInjectionRisk.MEDIUM.value,
                "message": "CHAR() encoding detected"
            })
        
        return issues
    
    def is_safe(self, sql: str) -> bool:
        """Quick check if SQL appears safe"""
        result = self.analyze(sql)
        return result.risk_level in (SQLInjectionRisk.NONE, SQLInjectionRisk.LOW)


class QuerySanitizer:
    """
    Sanitize and normalize SQL queries.
    """
    
    def __init__(self):
        self.detector = SQLInjectionDetector()
    
    def sanitize(self, sql: str) -> str:
        """
        Sanitize SQL query for safe execution.
        """
        # Remove comments
        sql = self._remove_comments(sql)
        
        # Normalize whitespace
        sql = " ".join(sql.split())
        
        # Validate allowed characters
        sql = self._validate_characters(sql)
        
        return sql.strip()
    
    def _remove_comments(self, sql: str) -> str:
        """Remove SQL comments"""
        # Remove single-line comments
        sql = re.sub(r'--[^\n]*', '', sql)
        
        # Remove block comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        return sql
    
    def _validate_characters(self, sql: str) -> str:
        """Ensure only safe characters are present"""
        # Allow standard SQL characters
        allowed = re.compile(r'^[\w\s\(\),.=<>!*+/\-_%\'"\:\\[\].$@#&|]*$', re.UNICODE)
        
        if not allowed.match(sql):
            # Find problematic characters
            for char in sql:
                if not allowed.match(char):
                    raise ValueError(f"Disallowed character in SQL: {repr(char)}")
        
        return sql
    
    def validate_identifiers(self, sql: str) -> List[Dict]:
        """
        Validate that all identifiers are safe.
        """
        issues = []
        
        # Extract identifiers (simplified)
        # This is a basic implementation - production would use proper SQL parsing
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                identifier = match.group(1)
                if not SQLInjectionDetector.SAFE_IDENTIFIER_CHARS.match(identifier):
                    issues.append({
                        "identifier": identifier,
                        "issue": "Invalid identifier format"
                    })
        
        return issues


class QueryWhitelist:
    """
    Whitelist-based query validation.
    Only allows pre-approved query patterns.
    """
    
    def __init__(self):
        self._allowed_patterns: Set[str] = set()
        self._allowed_tables: Set[str] = set()
    
    def add_allowed_pattern(self, pattern: str):
        """Add allowed query pattern (regex)"""
        self._allowed_patterns.add(pattern)
    
    def add_allowed_table(self, table: str):
        """Add allowed table name"""
        self._allowed_tables.add(table.lower())
    
    def is_allowed(self, sql: str) -> bool:
        """Check if query matches whitelist"""
        sql_upper = sql.upper()
        
        # Check table whitelist
        if self._allowed_tables:
            # Extract tables from query
            tables = self._extract_tables(sql)
            for table in tables:
                if table.lower() not in self._allowed_tables:
                    return False
        
        # Check pattern whitelist
        for pattern in self._allowed_patterns:
            if re.match(pattern, sql, re.IGNORECASE):
                return True
        
        return len(self._allowed_patterns) == 0  # Allow all if no patterns set
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL"""
        tables = []
        
        # FROM clause
        from_matches = re.finditer(
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            sql,
            re.IGNORECASE
        )
        tables.extend(m.group(1) for m in from_matches)
        
        # JOIN clause
        join_matches = re.finditer(
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            sql,
            re.IGNORECASE
        )
        tables.extend(m.group(1) for m in join_matches)
        
        return tables


class QueryBlacklist:
    """
    Blacklist-based query validation.
    Blocks known dangerous patterns.
    """
    
    def __init__(self):
        self._blocked_patterns: List[re.Pattern] = []
        self._blocked_tables: Set[str] = set()
        self._blocked_keywords: Set[str] = {
            'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE',
            'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'UNION'
        }
    
    def add_blocked_pattern(self, pattern: str):
        """Add regex pattern to block"""
        self._blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
    
    def add_blocked_table(self, table: str):
        """Add table name to block"""
        self._blocked_tables.add(table.lower())
    
    def is_blocked(self, sql: str) -> Optional[Dict]:
        """
        Check if query is blocked.
        Returns block reason or None if allowed.
        """
        sql_upper = sql.upper().strip()
        
        # Check for blocked keywords at start
        first_word = sql_upper.split()[0] if sql_upper else ""
        if first_word not in ('SELECT', 'WITH', '('):
            return {
                "blocked": True,
                "reason": f"Query must start with SELECT, not {first_word}"
            }
        
        # Check blocked keywords
        for keyword in self._blocked_keywords:
            if re.search(rf'\b{keyword}\b', sql_upper):
                return {
                    "blocked": True,
                    "reason": f"Forbidden keyword: {keyword}"
                }
        
        # Check blocked patterns
        for pattern in self._blocked_patterns:
            if pattern.search(sql):
                return {
                    "blocked": True,
                    "reason": f"Matches blocked pattern: {pattern.pattern[:30]}"
                }
        
        # Check blocked tables
        tables = self._extract_tables(sql)
        for table in tables:
            if table.lower() in self._blocked_tables:
                return {
                    "blocked": True,
                    "reason": f"Access to table blocked: {table}"
                }
        
        return None
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL"""
        tables = []
        
        from_matches = re.finditer(
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            sql,
            re.IGNORECASE
        )
        tables.extend(m.group(1) for m in from_matches)
        
        return tables


def validate_sql_security(
    sql: str,
    use_whitelist: bool = False,
    use_blacklist: bool = True,
    whitelist: Optional[QueryWhitelist] = None,
    blacklist: Optional[QueryBlacklist] = None
) -> SecurityCheckResult:
    """
    Comprehensive SQL security validation.
    """
    detector = SQLInjectionDetector()
    sanitizer = QuerySanitizer()
    
    # Run injection detection
    result = detector.analyze(sql)
    
    if not result.passed:
        return result
    
    # Check whitelist
    if use_whitelist and whitelist:
        if not whitelist.is_allowed(sql):
            return SecurityCheckResult(
                passed=False,
                risk_level=SQLInjectionRisk.HIGH,
                issues=[{"category": "whitelist", "message": "Query not in whitelist"}]
            )
    
    # Check blacklist
    if use_blacklist and blacklist:
        blocked = blacklist.is_blocked(sql)
        if blocked:
            return SecurityCheckResult(
                passed=False,
                risk_level=SQLInjectionRisk.CRITICAL,
                issues=[{"category": "blacklist", "message": blocked["reason"]}]
            )
    
    # Sanitize
    try:
        sanitized = sanitizer.sanitize(sql)
        result.sanitized_query = sanitized
    except ValueError as e:
        return SecurityCheckResult(
            passed=False,
            risk_level=SQLInjectionRisk.HIGH,
            issues=[{"category": "sanitization", "message": str(e)}]
        )
    
    return result
