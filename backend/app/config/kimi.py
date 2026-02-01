"""
Kimi AI Model Configuration
Supports Kimi K2.5 and other Moonshot AI models
"""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class KimiSettings(BaseSettings):
    """Kimi API configuration"""
    
    # API Configuration
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "kimi-k2.5"
    
    # Model parameters
    kimi_temperature: float = 0.1
    kimi_max_tokens: int = 4096
    kimi_timeout: int = 60
    
    class Config:
        env_file = ".env"
        env_prefix = "KIMI_"


@lru_cache()
def get_kimi_settings() -> KimiSettings:
    """Get cached Kimi settings"""
    return KimiSettings()


def get_kimi_client():
    """Initialize Kimi client (OpenAI-compatible)"""
    from openai import AsyncOpenAI
    settings = get_kimi_settings()
    
    if not settings.kimi_api_key or settings.kimi_api_key == "your-kimi-api-key-here":
        raise ValueError(
            "KIMI_API_KEY not configured. "
            "Get your API key from https://platform.moonshot.cn/"
        )
    
    return AsyncOpenAI(
        api_key=settings.kimi_api_key,
        base_url=settings.kimi_base_url,
        timeout=settings.kimi_timeout
    )


# Model capabilities
KIMI_CAPABILITIES = {
    "kimi-k2.5": {
        "context_window": 256000,
        "max_output_tokens": 8192,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": True,
    },
    "kimi-k2": {
        "context_window": 200000,
        "max_output_tokens": 4096,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": False,
    }
}


def get_model_capabilities(model: str) -> dict:
    """Get capabilities for a specific Kimi model"""
    return KIMI_CAPABILITIES.get(model, KIMI_CAPABILITIES["kimi-k2.5"])
