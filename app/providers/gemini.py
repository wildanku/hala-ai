"""
Google Gemini LLM Provider
"""

import json
from typing import Any, Optional, Literal
from app.providers.base import BaseLLMProvider
from app.core.config import settings


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM Provider.
    
    Uses google-generativeai SDK to interact with Gemini models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_model_name
        self._client = None
        self._model = None
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai
        return self._client
    
    def _get_model(self, response_format: str = "text"):
        """Get or create model instance with appropriate config."""
        genai = self._get_client()
        
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
        }
        
        if response_format == "json":
            generation_config["response_mime_type"] = "application/json"
        
        return genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=generation_config,
        )
    
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Generate response using Gemini."""
        
        model = self._get_model(response_format)
        
        # Combine system prompt and user message
        # Gemini uses a different format than OpenAI
        full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
        
        # Generate response
        response = await model.generate_content_async(
            full_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens or 8192,
            },
        )
        
        # Extract text from response
        text = response.text
        
        # Parse JSON if requested
        if response_format == "json":
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return self._parse_json_response(text)
        
        return {"content": text}
    
    async def health_check(self) -> bool:
        """Check if Gemini is available."""
        try:
            if not self._api_key:
                return False
            
            model = self._get_model()
            response = await model.generate_content_async("Say 'ok'")
            return bool(response.text)
        except Exception:
            return False
