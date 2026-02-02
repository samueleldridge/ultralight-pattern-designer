from enum import Enum
from typing import Dict, List, Optional, Any
import re


class SQLDialect(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"


class SQLValidator:
    """Dialect-aware SQL validation"""
    
    # Forbidden keywords for all dialects
    DANGEROUS_KEYWORDS = [
        'DELETE', 'DROP', 'TRUNCATE', 'UPDATE', 'INSERT', 
        'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
    ]
    
    def __init__(self, dialect: SQLDialect):
        self.dialect = dialect
    
    # Patterns that indicate SQL injection attempts
    RISKY_PATTERNS = [
        r';\s*DROP\s+',
        r';\s*DELETE\s+',
        r';\s*INSERT\s+',
        r';\s*UPDATE\s+',
        r'UNION\s+SELECT',
        r'UNION\s+ALL\s+SELECT',
        r'OR\s+\'\d+\'\s*=\s*\'\d+\'',
        r'OR\s+\d+\s*=\s*\d+',
        r'--\s*\+',
        r'/\*.*\*/',
        r';\s*EXEC\s*\(',
        r';\s*EXECUTE\s*\(',
    ]
    
    def validate(self, sql: str) -> Dict[str, Any]:
        """Validate SQL and return detailed results"""
        errors = []
        warnings = []
        
        # 1. Safety checks (critical)
        sql_upper = sql.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{keyword}\b', sql_upper):
                errors.append(f"Forbidden keyword detected: {keyword}")
        
        # 2. Check for SQL injection patterns
        risky = False
        for pattern in self.RISKY_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                risky = True
                errors.append(f"Potentially unsafe SQL pattern detected")
                break
        
        # 3. Must start with SELECT or WITH (for CTEs)
        sql_stripped = sql.strip().upper()
        if not (sql_stripped.startswith('SELECT') or sql_stripped.startswith('WITH')):
            errors.append("Query must start with SELECT or WITH (for CTEs)")
        
        # 3. Dialect-specific validation
        dialect_errors = self._validate_dialect_specific(sql)
        errors.extend(dialect_errors)
        
        # 4. Check for common mistakes
        warnings.extend(self._check_warnings(sql))
        
        # 5. Syntax validation (basic)
        syntax_errors = self._check_basic_syntax(sql)
        errors.extend(syntax_errors)
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "dialect": self.dialect
        }
        
        if risky:
            result["risky"] = True
            
        return result
    
    def _validate_dialect_specific(self, sql: str) -> List[str]:
        """Dialect-specific validation rules"""
        errors = []
        sql_upper = sql.upper()
        
        if self.dialect == SQLDialect.MYSQL:
            # MySQL specific checks
            if 'ILIKE' in sql_upper:
                errors.append("MySQL doesn't support ILIKE. Use LOWER() = LOWER() instead")
            if '::' in sql:  # PostgreSQL cast syntax
                errors.append("MySQL doesn't support :: casting. Use CAST() instead")
                
        elif self.dialect == SQLDialect.POSTGRESQL:
            # PostgreSQL specific checks
            if 'LIMIT' in sql_upper and ',' in sql:
                # Check for MySQL-style LIMIT
                limit_pattern = r'LIMIT\s+\d+\s*,\s*\d+'
                if re.search(limit_pattern, sql_upper):
                    errors.append("PostgreSQL uses LIMIT count OFFSET offset, not LIMIT offset, count")
                    
        elif self.dialect == SQLDialect.SNOWFLAKE:
            # Snowflake specific
            if sql_upper.startswith('SELECT *'):
                warnings.append("Snowflake charges by compute. Avoid SELECT * on large tables")
                
        elif self.dialect == SQLDialect.BIGQUERY:
            # BigQuery specific
            if not sql.startswith('`') and '.' in sql.split()[0]:
                warnings.append("BigQuery recommends backticks for project.dataset.table references")
        
        return errors
    
    def _check_warnings(self, sql: str) -> List[str]:
        """Check for performance/quality warnings"""
        warnings = []
        sql_upper = sql.upper()
        
        if 'SELECT *' in sql_upper:
            warnings.append("SELECT * can be slow on wide tables. Consider specifying columns")
        
        if 'WHERE' not in sql_upper and 'GROUP BY' not in sql_upper:
            warnings.append("No WHERE clause - query may return many rows")
        
        if sql_upper.count('JOIN') > 3:
            warnings.append("Many JOINs can impact performance. Consider denormalizing")
        
        if 'ORDER BY' not in sql_upper and 'LIMIT' in sql_upper:
            warnings.append("LIMIT without ORDER BY returns non-deterministic results")
        
        return warnings
    
    def _check_basic_syntax(self, sql: str) -> List[str]:
        """Basic syntax checks"""
        errors = []
        
        # Check for unmatched parentheses
        open_count = sql.count('(')
        close_count = sql.count(')')
        if open_count != close_count:
            errors.append(f"Unmatched parentheses: {open_count} open, {close_count} close")
        
        # Check for unmatched quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            errors.append("Unmatched single quotes")
        
        return errors
    
    def sanitize_for_execution(self, sql: str) -> str:
        """Sanitize SQL before execution"""
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Ensure read-only by double-checking no dangerous keywords
        sql_upper = sql.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{keyword}\b', sql_upper):
                raise ValueError(f"Security violation: {keyword} not allowed")
        
        return sql.strip()


class SQLDialectAdapter:
    """Adapt SQL between dialects"""
    
    @staticmethod
    def adapt_query(sql: str, from_dialect: SQLDialect, to_dialect: SQLDialect) -> str:
        """Adapt a query from one dialect to another"""
        if from_dialect == to_dialect:
            return sql
        
        adapted = sql
        
        # PostgreSQL to MySQL
        if from_dialect == SQLDialect.POSTGRESQL and to_dialect == SQLDialect.MYSQL:
            adapted = SQLDialectAdapter._postgres_to_mysql(adapted)
        
        # MySQL to PostgreSQL
        elif from_dialect == SQLDialect.MYSQL and to_dialect == SQLDialect.POSTGRESQL:
            adapted = SQLDialectAdapter._mysql_to_postgres(adapted)
        
        return adapted
    
    @staticmethod
    def _postgres_to_mysql(sql: str) -> str:
        """Convert PostgreSQL syntax to MySQL"""
        # ILIKE to LOWER comparison
        sql = re.sub(
            r'(\w+)\s+ILIKE\s+[\'"]([^\'"]+)[\'"]',
            r'LOWER(\1) = LOWER(\'\2\')',
            sql,
            flags=re.IGNORECASE
        )
        
        # :: casting to CAST
        sql = re.sub(
            r'(\w+)::(\w+)',
            r'CAST(\1 AS \2)',
            sql
        )
        
        # LIMIT offset, count to LIMIT count OFFSET offset
        sql = re.sub(
            r'LIMIT\s+(\d+)\s*,\s*(\d+)',
            r'LIMIT \2 OFFSET \1',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql
    
    @staticmethod
    def _mysql_to_postgres(sql: str) -> str:
        """Convert MySQL syntax to PostgreSQL"""
        # BACKTICKS to double quotes
        sql = re.sub(r'`([^`]+)`', r'"\1"', sql)
        
        # LIMIT offset, count format (MySQL) to LIMIT count OFFSET offset (PostgreSQL)
        sql = re.sub(
            r'LIMIT\s+(\d+)\s*,\s*(\d+)',
            r'LIMIT \2 OFFSET \1',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql
    
    @staticmethod
    def get_dialect_specific_prompt_hints(dialect: SQLDialect) -> dict:
        """Get prompt hints for LLM about dialect specifics"""
        hints = {
            SQLDialect.POSTGRESQL: {
                "identifier_style": "double quotes",
                "string_functions": "ILIKE supported for case-insensitive matching",
                "casting": "Use :: for casting (e.g., '2024-01-01'::DATE)",
                "pagination": "LIMIT n OFFSET m syntax",
                "date_functions": "NOW() returns timestamp with timezone",
                "backticks": False
            },
            SQLDialect.MYSQL: {
                "identifier_style": "backticks",
                "string_functions": "No ILIKE - use LOWER(column) = LOWER('value')",
                "casting": "Use CAST() for type casting, not ::",
                "pagination": "LIMIT offset, count syntax",
                "date_functions": "NOW() returns local timestamp",
                "backticks": True
            },
            SQLDialect.SNOWFLAKE: {
                "identifier_style": "database.schema.table qualification",
                "string_functions": "Standard SQL",
                "casting": "Use TO_TIMESTAMP() for date parsing",
                "pagination": "LIMIT n syntax",
                "date_functions": "Case-sensitive by default",
                "backticks": False
            },
            SQLDialect.BIGQUERY: {
                "identifier_style": "backticks for project.dataset.table",
                "string_functions": "Standard SQL",
                "casting": "Standard CAST",
                "pagination": "LIMIT n syntax",
                "date_functions": "Use CURRENT_TIMESTAMP() not NOW()",
                "backticks": True
            },
            SQLDialect.SQLSERVER: {
                "identifier_style": "square brackets [identifier]",
                "string_functions": "Standard SQL",
                "casting": "Standard CAST",
                "pagination": "Use TOP n instead of LIMIT",
                "date_functions": "GETDATE() instead of NOW()",
                "backticks": False
            },
            SQLDialect.SQLITE: {
                "identifier_style": "double quotes or none",
                "string_functions": "Standard SQL, no ILIKE",
                "casting": "CAST() function",
                "pagination": "LIMIT n OFFSET m",
                "date_functions": "DATE(), DATETIME(), STRFTIME()",
                "backticks": False
            }
        }
        
        return hints.get(dialect, {})
