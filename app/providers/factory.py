"""
LLM Provider Factory
Factory pattern for creating and managing LLM providers.
"""

from typing import Optional
from app.providers.base import BaseLLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAIProvider
from app.providers.ollama import OllamaProvider
from app.core.config import settings
from app.core.exceptions import ProviderNotFoundError


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.
    
    Supports:
    - Gemini (default)
    - OpenAI
    - Ollama (local)
    
    Usage:
        provider = LLMProviderFactory.create("gemini")
        provider = LLMProviderFactory.get_default()
    """
    
    _providers: dict[str, type[BaseLLMProvider]] = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    
    _instances: dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type[BaseLLMProvider],
    ) -> None:
        """Register a new provider type."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create(
        cls,
        provider_name: str,
        **kwargs,
    ) -> BaseLLMProvider:
        """
        Create a new provider instance.
        
        Args:
            provider_name: Name of the provider (gemini, openai, ollama)
            **kwargs: Additional arguments passed to provider constructor
            
        Returns:
            Configured LLM provider instance
            
        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        provider_class = cls._providers.get(provider_name.lower())
        
        if provider_class is None:
            raise ProviderNotFoundError(provider_name)
        
        return provider_class(**kwargs)
    
    @classmethod
    def get_or_create(
        cls,
        provider_name: str,
        **kwargs,
    ) -> BaseLLMProvider:
        """
        Get existing instance or create new one (singleton per provider).
        
        Useful for reusing connections and avoiding repeated initialization.
        """
        if provider_name not in cls._instances:
            cls._instances[provider_name] = cls.create(provider_name, **kwargs)
        return cls._instances[provider_name]
    
    @classmethod
    def get_default(cls) -> BaseLLMProvider:
        """Get the default provider based on settings."""
        return cls.get_or_create(settings.default_llm_provider)
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    async def check_provider_health(cls, provider_name: str) -> bool:
        """Check if a specific provider is healthy."""
        try:
            provider = cls.get_or_create(provider_name)
            return await provider.health_check()
        except Exception:
            return False
    
    @classmethod
    async def get_healthy_providers(cls) -> list[str]:
        """Get list of currently healthy providers."""
        healthy = []
        for name in cls._providers.keys():
            if await cls.check_provider_health(name):
                healthy.append(name)
        return healthy


def get_llm_provider(
    provider_name: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Convenience function to get an LLM provider.
    
    Args:
        provider_name: Optional provider name. Uses default if not specified.
        
    Returns:
        Configured LLM provider instance
    """
    if provider_name:
        return LLMProviderFactory.get_or_create(provider_name)
    return LLMProviderFactory.get_default()
