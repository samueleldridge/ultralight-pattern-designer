"""
LLM Provider module with Kimi K2.5 (Moonshot) primary support
and OpenAI fallback.
"""

import json
from typing import Optional, Any, AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.config import get_settings


class LLMProvider:
    """
    Unified LLM provider that supports multiple backends.
    Primary: Moonshot (Kimi K2.5)
    Fallback: OpenAI
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._moonshot_client: Optional[ChatOpenAI] = None
        self._openai_client: Optional[ChatOpenAI] = None
    
    @property
    def moonshot_client(self) -> Optional[ChatOpenAI]:
        """Lazy initialization of Moonshot client"""
        if self._moonshot_client is None and self.settings.moonshot_api_key:
            self._moonshot_client = ChatOpenAI(
                model=self.settings.moonshot_model,
                temperature=self.settings.moonshot_temperature,
                max_tokens=self.settings.moonshot_max_tokens,
                timeout=self.settings.moonshot_timeout,
                api_key=self.settings.moonshot_api_key,
                base_url=self.settings.moonshot_base_url,
                model_kwargs={
                    "top_p": 0.9,
                }
            )
        return self._moonshot_client
    
    @property
    def openai_client(self) -> Optional[ChatOpenAI]:
        """Lazy initialization of OpenAI client (fallback)"""
        if self._openai_client is None and self.settings.openai_api_key:
            self._openai_client = ChatOpenAI(
                model=self.settings.openai_model,
                temperature=0.1,
                api_key=self.settings.openai_api_key
            )
        return self._openai_client
    
    @property
    def primary_client(self) -> ChatOpenAI:
        """Get the primary LLM client"""
        if self.moonshot_client:
            return self.moonshot_client
        if self.openai_client:
            return self.openai_client
        raise RuntimeError(
            "No LLM provider configured. "
            "Set MOONSHOT_API_KEY or OPENAI_API_KEY in .env"
        )
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None
    ) -> str:
        """
        Generate text from prompt using primary LLM.
        Falls back to secondary provider if primary fails.
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Try primary (Moonshot/Kimi K2.5)
        try:
            client = self.primary_client
            
            # Override params if provided
            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await client.ainvoke(messages, **kwargs)
            return response.content
            
        except Exception as e:
            # Try fallback (OpenAI)
            if self.openai_client and self.moonshot_client:
                print(f"Moonshot failed, trying OpenAI fallback: {e}")
                try:
                    response = await self.openai_client.ainvoke(messages)
                    return response.content
                except Exception as fallback_error:
                    raise RuntimeError(
                        f"Both primary and fallback LLMs failed. "
                        f"Primary error: {e}, Fallback error: {fallback_error}"
                    )
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> dict:
        """
        Generate and parse JSON response.
        """
        # For Moonshot/Kimi, we can use response_format
        if self.moonshot_client:
            response_format = {"type": "json_object"}
            content = await self.generate(
                prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                response_format=response_format
            )
        else:
            # For OpenAI, add JSON instruction to prompt
            json_prompt = prompt + "\n\nRespond with valid JSON only."
            content = await self.generate(
                json_prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {content[:500]}")
    
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream text generation.
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        client = self.primary_client
        
        async for chunk in client.astream(messages):
            if chunk.content:
                yield chunk.content


# Global instance
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get or create global LLM provider instance"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider


# Backward compatibility
async def generate_with_kimi(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1
) -> str:
    """
    Convenience function for direct Kimi K2.5 usage.
    Maintains backward compatibility with existing code.
    """
    provider = get_llm_provider()
    return await provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature
    )
