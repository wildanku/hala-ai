"""
Base LLM Provider
Abstract base class for all LLM providers using Strategy Pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Literal


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    
    content: Any  # Can be string or parsed JSON
    model: str
    provider: str
    usage: Optional[dict[str, int]] = None  # Token usage info
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None  # Original provider response


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Implement this interface to add new LLM providers (Gemini, OpenAI, Ollama, etc.)
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model being used by this provider."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: The system instruction/context
            user_message: The user's message/query
            response_format: Expected response format ("text" or "json")
            temperature: Creativity parameter (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Parsed response (dict for JSON, str for text)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and configured."""
        pass
    
    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Helper to parse JSON from LLM response."""
        import json
        
        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        return json.loads(text)
