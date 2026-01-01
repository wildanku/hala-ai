"""
Google Gemini LLM Provider
Using the new google.genai package (recommended)
"""

import json
import re
import logging
from typing import Any, Optional, Literal
from app.providers.base import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM Provider.
    
    Uses google.genai SDK to interact with Gemini models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_model_name
        self._client = None
        
        if not self._api_key:
            logger.error("Gemini API key not found in settings")
        else:
            logger.info(f"Gemini initialized with model: {self._model_name}")
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client
    
    def _clean_and_parse_json(self, text: str) -> dict[str, Any]:
        """Clean and parse JSON response with multiple fallback strategies."""
        
        # Strategy 1: Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find first { to last } (assuming single JSON object)
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            json_candidate = text[start:end]
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                # Strategy 4: Try to fix common JSON issues
                fixed = json_candidate
                # Fix trailing commas
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r',\s*]', ']', fixed)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        
        # Final fallback: raise error
        raise json.JSONDecodeError("Could not parse JSON after all cleanup attempts", text, 0)
    
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Generate response using Gemini."""
        
        try:
            client = self._get_client()
            
            # Combine system prompt and user message
            full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
            
            logger.info(f"Generating with Gemini model: {self._model_name}")
            
            # Build config - use higher token limit for complex responses
            config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens or 32768,  # Increased for longer journeys
            }
            
            if response_format == "json":
                config["response_mime_type"] = "application/json"
            
            # Generate response using new API
            response = await client.aio.models.generate_content(
                model=self._model_name,
                contents=full_prompt,
                config=config,
            )
            
            # Extract text from response
            text = response.text
            
            # Parse JSON if requested
            if response_format == "json":
                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {str(e)}")
                    
                    try:
                        return self._clean_and_parse_json(text)
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse JSON after cleanup: {str(e2)}")
                        # Return a minimal working structure
                        return self._get_fallback_response()
            
            return {"content": text}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini API error: {error_msg}")
            
            # Handle specific errors
            if "429" in error_msg or "quota" in error_msg.lower():
                raise Exception(f"Gemini API quota exceeded. Model: {self._model_name}. Try again later.")
            elif "401" in error_msg or "authentication" in error_msg.lower():
                raise Exception("Gemini API authentication failed. Check your API key.")
            elif "400" in error_msg:
                raise Exception("Gemini API request error. Check your prompt format.")
            else:
                raise Exception(f"Gemini API error: {error_msg}")
    
    def _get_fallback_response(self) -> dict[str, Any]:
        """Return a minimal fallback response when JSON parsing fails."""
        return {
            "goal": "Unable to parse response",
            "total_days": 7,
            "introduction": {
                "id": "Maaf, terjadi kesalahan dalam memproses respons.",
                "en": "Sorry, there was an error processing the response."
            },
            "goal_keyword": "parse-error",
            "tags": ["error"],
            "journey": [
                {
                    "day": "1",
                    "type": "reflection",
                    "time": "morning",
                    "title": {
                        "id": "Refleksi dan Doa",
                        "en": "Reflection and Prayer"
                    },
                    "description": {
                        "id": "Luangkan waktu untuk merefleksikan niat spiritual Anda.",
                        "en": "Take time to reflect on your spiritual intentions."
                    }
                }
            ]
        }
    
    async def health_check(self) -> bool:
        """Check if Gemini is available."""
        try:
            if not self._api_key:
                logger.error("No API key available for health check")
                return False
            
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self._model_name,
                contents="Say 'ok'",
            )
            result = bool(response.text)
            logger.info(f"Health check passed: {result}")
            return result
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
