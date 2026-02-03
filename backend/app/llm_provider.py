"""
LLM Provider module - Backward compatibility wrapper

New code should use: from app.llm_factory import get_llm_provider

This module maintains backward compatibility with existing imports.
"""

from typing import Optional, Dict, Any

# Re-export from new factory module for backward compatibility
from app.llm_factory import (
    get_llm_provider,
    LLMProviderFactory,
    LLMProviderType,
    LLMResponse,
    MoonshotProvider,
    OpenAIProvider,
    AnthropicProvider,
    BaseLLMProvider,
)

# For backward compatibility - map new factory to old interface
class LLMProvider:
    """
    Backward-compatible LLM Provider wrapper.
    
    New code should use:
        from app.llm_factory import get_llm_provider
        provider = get_llm_provider()  # or get_llm_provider("moonshot")
    """
    
    def __init__(self):
        self._provider = None
    
    def _get_provider(self):
        """Lazy load the underlying provider"""
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider
    
    @property
    def moonshot_client(self):
        """Get Moonshot client (for backward compatibility)"""
        try:
            return LLMProviderFactory.get_provider("moonshot")
        except Exception:
            return None
    
    @property
    def openai_client(self):
        """Get OpenAI client (for backward compatibility)"""
        try:
            return LLMProviderFactory.get_provider("openai")
        except Exception:
            return None
    
    @property
    def primary_client(self):
        """Get primary client (for backward compatibility)"""
        return self._get_provider()
    
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
    ) -> Dict[str, Any]:
        """Generate JSON (backward compatible)"""
        provider = self._get_provider()
        return await provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature or 0.1,
            max_tokens=max_tokens
        )
    
    async def stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Stream generation (backward compatible)"""
        # This is a simplified implementation
        content = await self.generate(prompt, system_prompt)
        yield content


# Global instance for backward compatibility
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider_legacy() -> LLMProvider:
    """Get or create global LLM provider instance (backward compatible)"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider


# Alias for new code
get_llm_provider_new = get_llm_provider


# Convenience functions for specific providers
def get_moonshot_provider():
    """Get Moonshot/Kimi K2.5 provider"""
    return LLMProviderFactory.get_provider("moonshot")


def get_openai_provider():
    """Get OpenAI provider"""
    return LLMProviderFactory.get_provider("openai")


def get_anthropic_provider():
    """Get Anthropic/Claude provider"""
    return LLMProviderFactory.get_provider("anthropic")


async def generate_with_kimi(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1
) -> str:
    """Convenience function for direct Kimi K2.5 usage"""
    provider = get_moonshot_provider()
    response = await provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature
    )
    
    if response.error:
        raise RuntimeError(f"Kimi generation failed: {response.error}")
    
    return response.content
