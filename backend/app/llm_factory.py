"""
Multi-Provider LLM Support

Supports:
- Moonshot (Kimi K2.5) - Primary
- OpenAI (GPT-4, GPT-3.5) - Fallback
- Anthropic (Claude) - Optional
- Local models (via OpenAI-compatible API)

Usage:
    from app.llm_factory import get_llm_provider
    
    provider = get_llm_provider("moonshot")  # or "openai", "anthropic"
    response = await provider.generate("Generate SQL for...")
"""

import json
from typing import Optional, Any, Dict, List
from enum import Enum
from dataclasses import dataclass

from app.config import get_settings


class LLMProviderType(Enum):
    MOONSHOT = "moonshot"      # Kimi K2.5
    OPENAI = "openai"          # GPT-4, GPT-3.5
    ANTHROPIC = "anthropic"    # Claude
    LOCAL = "local"            # Local models (Ollama, etc.)
    AZURE = "azure"            # Azure OpenAI


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict] = None
    error: Optional[str] = None


class BaseLLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        raise NotImplementedError
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Generate and parse JSON response"""
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        if response.error:
            return {"error": response.error}
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "raw": response.content}


class MoonshotProvider(BaseLLMProvider):
    """Moonshot AI (Kimi K2.5) Provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._init_client()
    
    def _init_client(self):
        """Initialize Moonshot client"""
        try:
            from langchain_openai import ChatOpenAI
            
            self.client = ChatOpenAI(
                model=self.config.get("model", "kimi-k2-5"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 16384),
                timeout=self.config.get("timeout", 120),
                api_key=self.config["api_key"],
                base_url=self.config.get("base_url", "https://api.moonshot.cn/v1"),
                model_kwargs={
                    "top_p": 0.9,
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Moonshot client: {e}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Generate using Moonshot/Kimi K2.5"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await self.client.ainvoke(messages, **kwargs)
            
            return LLMResponse(
                content=response.content,
                provider="moonshot",
                model=self.config.get("model", "kimi-k2-5"),
                usage=getattr(response, 'usage', None)
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                provider="moonshot",
                model=self.config.get("model", "kimi-k2-5"),
                error=str(e)
            )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-4, GPT-3.5)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            from langchain_openai import ChatOpenAI
            
            self.client = ChatOpenAI(
                model=self.config.get("model", "gpt-4"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 4096),
                api_key=self.config["api_key"]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Generate using OpenAI"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await self.client.ainvoke(messages, **kwargs)
            
            return LLMResponse(
                content=response.content,
                provider="openai",
                model=self.config.get("model", "gpt-4"),
                usage=getattr(response, 'usage', None)
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                provider="openai",
                model=self.config.get("model", "gpt-4"),
                error=str(e)
            )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Provider (Claude)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._init_client()
    
    def _init_client(self):
        """Initialize Anthropic client"""
        try:
            from langchain_anthropic import ChatAnthropic
            
            self.client = ChatAnthropic(
                model=self.config.get("model", "claude-3-sonnet-20240229"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 4096),
                api_key=self.config["api_key"]
            )
        except ImportError:
            raise RuntimeError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Anthropic client: {e}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Generate using Anthropic Claude"""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            
            response = await self.client.ainvoke(messages, **kwargs)
            
            return LLMResponse(
                content=response.content,
                provider="anthropic",
                model=self.config.get("model", "claude-3-sonnet"),
                usage=getattr(response, 'usage', None)
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                provider="anthropic",
                model=self.config.get("model", "claude-3-sonnet"),
                error=str(e)
            )


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    _providers: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def create_provider(cls, provider_type: LLMProviderType, config: Dict[str, Any]) -> BaseLLMProvider:
        """Create a provider instance"""
        if provider_type == LLMProviderType.MOONSHOT:
            return MoonshotProvider(config)
        elif provider_type == LLMProviderType.OPENAI:
            return OpenAIProvider(config)
        elif provider_type == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
    
    @classmethod
    def get_provider(cls, provider_name: str) -> BaseLLMProvider:
        """Get or create a provider by name"""
        if provider_name in cls._providers:
            return cls._providers[provider_name]
        
        settings = get_settings()
        
        if provider_name == "moonshot":
            config = {
                "api_key": settings.moonshot_api_key,
                "base_url": settings.moonshot_base_url,
                "model": settings.moonshot_model,
                "temperature": settings.moonshot_temperature,
                "max_tokens": settings.moonshot_max_tokens,
                "timeout": settings.moonshot_timeout,
            }
            provider = cls.create_provider(LLMProviderType.MOONSHOT, config)
            cls._providers[provider_name] = provider
            return provider
        
        elif provider_name == "openai":
            config = {
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
                "temperature": 0.1,
            }
            provider = cls.create_provider(LLMProviderType.OPENAI, config)
            cls._providers[provider_name] = provider
            return provider
        
        elif provider_name == "anthropic":
            config = {
                "api_key": getattr(settings, 'anthropic_api_key', ''),
                "model": getattr(settings, 'anthropic_model', 'claude-3-sonnet-20240229'),
                "temperature": 0.1,
            }
            provider = cls.create_provider(LLMProviderType.ANTHROPIC, config)
            cls._providers[provider_name] = provider
            return provider
        
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    @classmethod
    def get_primary_provider(cls) -> BaseLLMProvider:
        """Get the primary provider (Moonshot/Kimi preferred)"""
        settings = get_settings()
        
        # Try Moonshot first (Kimi K2.5)
        if settings.moonshot_api_key and not settings.moonshot_api_key.startswith("sk-test"):
            try:
                return cls.get_provider("moonshot")
            except Exception:
                pass
        
        # Fall back to OpenAI
        if settings.openai_api_key and not settings.openai_api_key.startswith("sk-test"):
            try:
                return cls.get_provider("openai")
            except Exception:
                pass
        
        # Try Anthropic
        if getattr(settings, 'anthropic_api_key', None):
            try:
                return cls.get_provider("anthropic")
            except Exception:
                pass
        
        raise RuntimeError(
            "No LLM provider configured. "
            "Set MOONSHOT_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env"
        )


# Convenience function
def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """
    Get LLM provider instance.
    
    Args:
        provider_name: Specific provider ("moonshot", "openai", "anthropic")
                      If None, returns primary provider
    
    Returns:
        Configured LLM provider
    """
    if provider_name:
        return LLMProviderFactory.get_provider(provider_name)
    return LLMProviderFactory.get_primary_provider()


# Backward compatibility
class LLMProvider:
    """Backward-compatible wrapper"""
    
    def __init__(self):
        self._provider = None
    
    def _get_provider(self):
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> str:
        """Generate text (backward compatible)"""
        provider = self._get_provider()
        response = await provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature or 0.1,
            max_tokens=max_tokens,
            response_format=response_format
        )
        
        if response.error:
            raise RuntimeError(f"LLM generation failed: {response.error}")
        
        return response.content
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Generate JSON (backward compatible)"""
        provider = self._get_provider()
        return await provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature or 0.1,
            max_tokens=max_tokens
        )


# Legacy function
def get_llm_provider_legacy() -> LLMProvider:
    """Get legacy LLM provider wrapper"""
    return LLMProvider()
