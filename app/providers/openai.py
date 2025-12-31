"""
OpenAI LLM Provider (GPT-4, GPT-4o, etc.)
Ready for future integration.
"""

import json
from typing import Any, Optional, Literal
from app.providers.base import BaseLLMProvider
from app.core.config import settings


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM Provider.
    
    Uses openai SDK to interact with GPT models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._api_key = api_key or settings.openai_api_key
        self._model_name = model_name or settings.openai_model_name
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client
    
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Generate response using OpenAI."""
        
        client = self._get_client()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await client.chat.completions.create(**kwargs)
        
        text = response.choices[0].message.content
        
        if response_format == "json":
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return self._parse_json_response(text)
        
        return {"content": text}
    
    async def health_check(self) -> bool:
        """Check if OpenAI is available."""
        try:
            if not self._api_key:
                return False
            
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)
        except Exception:
            return False
