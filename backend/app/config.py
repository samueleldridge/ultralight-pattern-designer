from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List
import os


class Settings(BaseSettings):
    """
    Application settings with support for Kimi K2.5 and multiple LLM providers.
    All settings can be overridden via environment variables.
    """
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    app_name: str = "AI Analytics Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    request_timeout: int = 300
    
    # =============================================================================
    # SECURITY SETTINGS
    # =============================================================================
    secret_key: str = "change-this-in-production-min-32-chars"
    jwt_secret_key: str = "jwt-secret-change-in-production"
    encryption_key: str = "encryption-key-16"
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # =============================================================================
    # DATABASE SETTINGS (SQLite by default for easy startup)
    # =============================================================================
    database_url: str = "sqlite+aiosqlite:///./ai_analytics.db"
    direct_database_url: Optional[str] = None
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # =============================================================================
    # SUPABASE SETTINGS
    # =============================================================================
    supabase_url: str = ""
    supabase_service_key: str = ""  # service_role key
    supabase_anon_key: str = ""     # anon/public key
    
    # =============================================================================
    # REDIS SETTINGS
    # =============================================================================
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    cache_ttl: int = 3600  # 1 hour
    
    # =============================================================================
    # PRIMARY AI: MOONSHOT / KIMI K2.5
    # =============================================================================
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    moonshot_model: str = "kimi-k2-5"
    moonshot_max_tokens: int = 16384
    moonshot_temperature: float = 0.1
    moonshot_timeout: int = 120
    
    # Fallback to OpenAI if Moonshot fails
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-0125-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # =============================================================================
    # AUTHENTICATION (Clerk)
    # =============================================================================
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: Optional[str] = None
    
    # =============================================================================
    # OBSERVABILITY
    # =============================================================================
    # Langfuse
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # PostHog
    posthog_api_key: Optional[str] = None
    posthog_host: str = "https://app.posthog.com"
    
    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    enable_proactive_insights: bool = True
    enable_rag: bool = True
    enable_collaboration: bool = True
    enable_query_cache: bool = True
    
    # =============================================================================
    # LOGGING
    # =============================================================================
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def primary_llm_provider(self) -> str:
        """Determine primary LLM provider based on available keys"""
        if self.moonshot_api_key and self.moonshot_api_key.startswith("sk-proj-"):
            return "moonshot"
        elif self.openai_api_key:
            return "openai"
        return "none"
    
    @property
    def has_valid_llm_config(self) -> bool:
        """Check if at least one LLM provider is configured"""
        return self.primary_llm_provider != "none"
    
    @property
    def database_url_safe(self) -> str:
        """Return database URL with password masked for logging"""
        if self.database_url:
            # Simple masking - in production use proper URL parsing
            parts = self.database_url.split("@")
            if len(parts) > 1:
                creds = parts[0].split(":")
                if len(creds) > 2:
                    return f"{creds[0]}:****@{parts[1]}"
        return self.database_url or "not-set"
    
    @property
    def embedding_model(self) -> str:
        """Alias for openai_embedding_model for backward compatibility"""
        return self.openai_embedding_model


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid reloading .env on every request.
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Force reload settings from .env file.
    Useful for testing or when environment changes.
    """
    get_settings.cache_clear()
    return get_settings()


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_critical_settings() -> list[str]:
    """
    Validate that all critical settings are configured.
    Returns list of missing/invalid settings.
    """
    settings = get_settings()
    errors = []
    
    # Check LLM provider
    if not settings.has_valid_llm_config:
        errors.append("No valid LLM provider configured. Set MOONSHOT_API_KEY or OPENAI_API_KEY")
    
    # Check Supabase
    if not settings.supabase_url:
        errors.append("SUPABASE_URL not set")
    if not settings.supabase_service_key:
        errors.append("SUPABASE_SERVICE_KEY not set")
    
    # Check Clerk
    if not settings.clerk_secret_key:
        errors.append("CLERK_SECRET_KEY not set")
    
    # Check database
    if not settings.database_url or settings.database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics":
        errors.append("DATABASE_URL not properly configured (using default)")
    
    # Security warnings
    if settings.secret_key == "change-this-in-production-min-32-chars":
        errors.append("SECRET_KEY is using default value - change for production")
    
    return errors
