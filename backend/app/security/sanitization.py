"""
Input sanitization utilities.
Clean and validate all user inputs.
"""

import re
import html
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class InputType(Enum):
    """Types of input data"""
    SQL_IDENTIFIER = "sql_identifier"
    SQL_LITERAL = "sql_literal"
    EMAIL = "email"
    URL = "url"
    JSON = "json"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    UUID = "uuid"


class InputValidator:
    """Validate user inputs"""
    
    # Validation patterns
    PATTERNS = {
        'sql_identifier': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE),
        'safe_string': re.compile(r'^[\w\s\-_.@]*$'),
    }
    
    MAX_LENGTHS = {
        'sql_identifier': 128,
        'plain_text': 10000,
        'email': 254,
        'url': 2048,
    }
    
    @classmethod
    def validate(
        cls,
        value: Any,
        input_type: InputType,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allowed_values: Optional[List] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate input value.
        Returns (is_valid, error_message)
        """
        # Check required
        if required and value is None:
            return False, "Value is required"
        
        if not required and (value is None or value == ""):
            return True, None
        
        # Convert to string for validation
        str_value = str(value)
        
        # Check length
        if min_length is not None and len(str_value) < min_length:
            return False, f"Minimum length is {min_length}"
        
        max_len = max_length or cls.MAX_LENGTHS.get(input_type.value)
        if max_len and len(str_value) > max_len:
            return False, f"Maximum length is {max_len}"
        
        # Check allowed values
        if allowed_values is not None:
            if value not in allowed_values:
                return False, f"Value must be one of: {allowed_values}"
            return True, None
        
        # Type-specific validation
        validators = {
            InputType.SQL_IDENTIFIER: cls._validate_sql_identifier,
            InputType.EMAIL: cls._validate_email,
            InputType.UUID: cls._validate_uuid,
            InputType.INTEGER: cls._validate_integer,
            InputType.FLOAT: cls._validate_float,
            InputType.BOOLEAN: cls._validate_boolean,
            InputType.URL: cls._validate_url,
        }
        
        validator = validators.get(input_type)
        if validator:
            return validator(str_value)
        
        return True, None
    
    @classmethod
    def _validate_sql_identifier(cls, value: str) -> tuple[bool, Optional[str]]:
        if not cls.PATTERNS['sql_identifier'].match(value):
            return False, "Invalid SQL identifier"
        if len(value) > cls.MAX_LENGTHS['sql_identifier']:
            return False, f"Identifier too long (max {cls.MAX_LENGTHS['sql_identifier']})"
        # Check against SQL keywords
        sql_keywords = {'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'DROP'}
        if value.upper() in sql_keywords:
            return False, "Cannot use SQL keywords as identifiers"
        return True, None
    
    @classmethod
    def _validate_email(cls, value: str) -> tuple[bool, Optional[str]]:
        if not cls.PATTERNS['email'].match(value):
            return False, "Invalid email format"
        return True, None
    
    @classmethod
    def _validate_uuid(cls, value: str) -> tuple[bool, Optional[str]]:
        if not cls.PATTERNS['uuid'].match(value):
            return False, "Invalid UUID format"
        return True, None
    
    @classmethod
    def _validate_integer(cls, value: str) -> tuple[bool, Optional[str]]:
        try:
            int(value)
            return True, None
        except ValueError:
            return False, "Invalid integer"
    
    @classmethod
    def _validate_float(cls, value: str) -> tuple[bool, Optional[str]]:
        try:
            float(value)
            return True, None
        except ValueError:
            return False, "Invalid number"
    
    @classmethod
    def _validate_boolean(cls, value: str) -> tuple[bool, Optional[str]]:
        if value.lower() in ('true', 'false', '1', '0', 'yes', 'no'):
            return True, None
        return False, "Invalid boolean value"
    
    @classmethod
    def _validate_url(cls, value: str) -> tuple[bool, Optional[str]]:
        if len(value) > cls.MAX_LENGTHS['url']:
            return False, "URL too long"
        if not value.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"
        return True, None


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks"""
    
    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """
        Sanitize SQL identifier (table/column name).
        Only allows alphanumeric and underscore.
        """
        # Remove any non-identifier characters
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
        
        # Ensure starts with letter or underscore
        if cleaned and not re.match(r'^[a-zA-Z_]', cleaned):
            cleaned = '_' + cleaned
        
        # Limit length
        return cleaned[:128]
    
    @staticmethod
    def sanitize_sql_literal(value: str) -> str:
        """
        Sanitize SQL string literal.
        Escapes quotes and removes null bytes.
        """
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape single quotes
        value = value.replace("'", "''")
        
        return value
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Sanitize HTML content.
        Escapes all HTML special characters.
        """
        return html.escape(text)
    
    @staticmethod
    def sanitize_plain_text(text: str, max_length: int = 10000) -> str:
        """
        Sanitize plain text.
        Removes control characters and limits length.
        """
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Limit length
        return text[:max_length]
    
    @staticmethod
    def sanitize_json(data: Any) -> Any:
        """
        Sanitize JSON data recursively.
        """
        if isinstance(data, dict):
            return {
                InputSanitizer.sanitize_plain_text(str(k)): InputSanitizer.sanitize_json(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [InputSanitizer.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            return InputSanitizer.sanitize_plain_text(data)
        elif isinstance(data, (int, float, bool)) or data is None:
            return data
        else:
            return str(data)
    
    @classmethod
    def sanitize(cls, value: Any, input_type: InputType) -> Any:
        """
        Sanitize value based on input type.
        """
        sanitizers = {
            InputType.SQL_IDENTIFIER: cls.sanitize_sql_identifier,
            InputType.SQL_LITERAL: cls.sanitize_sql_literal,
            InputType.HTML: cls.sanitize_html,
            InputType.PLAIN_TEXT: cls.sanitize_plain_text,
            InputType.JSON: cls.sanitize_json,
        }
        
        sanitizer = sanitizers.get(input_type)
        if sanitizer and isinstance(value, str):
            return sanitizer(value)
        
        return value


class ParameterValidator:
    """Validate API parameters"""
    
    def __init__(self):
        self.errors: Dict[str, str] = {}
    
    def add_error(self, field: str, message: str):
        """Add validation error"""
        self.errors[field] = message
    
    def has_errors(self) -> bool:
        """Check if there are validation errors"""
        return len(self.errors) > 0
    
    def validate_field(
        self,
        field: str,
        value: Any,
        input_type: InputType,
        required: bool = True,
        **kwargs
    ) -> Any:
        """
        Validate a single field.
        Returns sanitized value or adds error.
        """
        is_valid, error = InputValidator.validate(value, input_type, required, **kwargs)
        
        if not is_valid:
            self.add_error(field, error)
            return None
        
        # Sanitize if valid
        return InputSanitizer.sanitize(value, input_type)
    
    def validate_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Validate data against a schema.
        Schema format: {field: {type, required, min, max, ...}}
        """
        result = {}
        
        for field, config in schema.items():
            value = data.get(field)
            input_type = config.get('type', InputType.PLAIN_TEXT)
            required = config.get('required', True)
            
            validated = self.validate_field(
                field,
                value,
                input_type,
                required,
                min_length=config.get('min_length'),
                max_length=config.get('max_length'),
                allowed_values=config.get('allowed')
            )
            
            if field not in self.errors:
                result[field] = validated
        
        return result
    
    def raise_if_errors(self):
        """Raise exception if there are errors"""
        if self.errors:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": self.errors}
            )


def sanitize_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize query parameters.
    """
    sanitized = {}
    
    for key, value in params.items():
        # Sanitize key
        clean_key = InputSanitizer.sanitize_sql_identifier(key)
        
        # Sanitize value based on type
        if isinstance(value, str):
            clean_value = InputSanitizer.sanitize_plain_text(value)
        elif isinstance(value, (int, float, bool)):
            clean_value = value
        elif isinstance(value, list):
            clean_value = [
                InputSanitizer.sanitize_plain_text(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            clean_value = str(value)
        
        sanitized[clean_key] = clean_value
    
    return sanitized
