"""
Ollama LLM Provider (Local LLM - Llama, Mistral, etc.)
Ready for future integration with self-hosted models.
"""

import json
from typing import Any, Optional, Literal
import httpx
from app.providers.base import BaseLLMProvider
from app.core.config import settings


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM Provider for local/self-hosted models.
    
    Supports models like Llama 3, Mistral, Phi, etc.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._base_url = base_url or settings.ollama_base_url
        self._model_name = model_name or settings.ollama_model_name
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Generate response using Ollama."""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self._model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }
            
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            if response_format == "json":
                payload["format"] = "json"
            
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            text = data["message"]["content"]
            
            if response_format == "json":
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return self._parse_json_response(text)
            
            return {"content": text}
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
