"""
Layer 5: Prompt Enrichment & LLM Inference
The final stage where validated input and retrieved context are sent to the LLM.
"""

import time
from typing import Optional, Any
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult


# System prompt template for journey generation - Single language based on user input
JOURNEY_SYSTEM_PROMPT = """You are Hala Journal's AI companion, specializing in creating personalized spiritual and productivity journeys based on authentic Islamic sources.

STRICT RULES:
1. You MUST ONLY use the verses, hadith, and strategies provided in the CONTEXT below
2. NEVER fabricate or hallucinate any Quran verse or Hadith
3. If the context doesn't contain enough information, acknowledge this limitation
4. Always cite the source (Surah:Ayah for Quran, Book for Hadith)
5. DETECT the user's input language and respond ONLY in that same language
6. Include the "language" field in output with value "id" for Indonesian or "en" for English
7. Do NOT provide bilingual translations - respond in ONE language only

CONTEXT FROM KNOWLEDGE BASE:
{context}

USER'S DETECTED SCOPE: {scope}
DETECTED LANGUAGE: {language}
"""

JOURNEY_OUTPUT_FORMAT = """
Generate a 14-day spiritual journey in the following JSON format.
IMPORTANT: All text content (journey_title, journey_description, theme, title, description, prompt, questions) 
must be in the detected user language ONLY. Do not provide translations.

{{
    "language": "<id or en based on user input>",
    "journey_title": "<title in user's language>",
    "journey_description": "<description in user's language>",
    "scope": "string",
    "days": [
        {{
            "day": 1,
            "theme": "<theme in user's language>",
            "morning_task": {{
                "title": "<title in user's language>",
                "description": "<description in user's language>",
                "verse_reference": "string (optional)",
                "hadith_reference": "string (optional)"
            }},
            "evening_reflection": {{
                "prompt": "<prompt in user's language>",
                "journaling_questions": ["<questions in user's language>"]
            }}
        }}
    ],
    "sources_used": {{
        "verses": ["string"],
        "hadith": ["string"],
        "strategies": ["string"]
    }}
}}
"""


class LLMInferenceLayer(PipelineLayer):
    """
    Layer 5: LLM Inference with prompt enrichment.
    
    Combines:
    - Validated user input
    - Retrieved RAG context
    - Structured system prompt
    
    Then sends to the LLM provider for generation.
    """
    
    def __init__(
        self,
        llm_provider=None,
        custom_system_prompt: Optional[str] = None,
        custom_output_format: Optional[str] = None,
    ):
        self._llm_provider = llm_provider
        self._system_prompt = custom_system_prompt or JOURNEY_SYSTEM_PROMPT
        self._output_format = custom_output_format or JOURNEY_OUTPUT_FORMAT
    
    @property
    def layer_name(self) -> str:
        return "llm_inference"
    
    @property
    def layer_order(self) -> int:
        return 5
    
    def set_llm_provider(self, llm_provider):
        """Set LLM provider (dependency injection)."""
        self._llm_provider = llm_provider
    
    async def process(self, context: PipelineContext) -> PipelineResult:
        start_time = time.perf_counter()
        
        if self._llm_provider is None:
            return self._create_error_result(
                message="LLM provider not initialized",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        try:
            # Build the context string from retrieved documents
            context_str = self._build_context_string(context)
            
            # Get detected language from context (set by Layer 1)
            detected_language = context.detected_language or context.language
            language_name = "Indonesian" if detected_language == "id" else "English"
            
            # Build the full system prompt with language
            system_prompt = self._system_prompt.format(
                context=context_str,
                scope=context.detected_scope or "general",
                language=f"{language_name} ({detected_language})",
            )
            
            # Build the user message with language instruction
            user_message = f"""
User's Request: {context.processed_input}
Detected Language: {language_name} ({detected_language})

IMPORTANT: Respond ONLY in {language_name}. Do not provide translations.

{self._output_format}
"""
            
            # Call the LLM provider
            response = await self._llm_provider.generate(
                system_prompt=system_prompt,
                user_message=user_message,
                response_format="json",
            )
            
            # Store response in context
            context.llm_response = response
            context.llm_provider_used = self._llm_provider.provider_name
            
            execution_time = (time.perf_counter() - start_time) * 1000
            context.layer_timings[self.layer_name] = execution_time
            
            return self._create_success_result(
                message=f"LLM inference completed using {self._llm_provider.provider_name}",
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            return self._create_error_result(
                message=f"LLM inference error: {str(e)}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
    
    def _build_context_string(self, context: PipelineContext) -> str:
        """Build a formatted context string from retrieved documents."""
        sections = []
        
        # Quran verses
        if context.retrieved_verses:
            verses_text = "\n".join([
                f"- {v.get('reference', 'Unknown')}: {v.get('text', '')}"
                for v in context.retrieved_verses
            ])
            sections.append(f"QURAN VERSES:\n{verses_text}")
        
        # Hadith
        if context.retrieved_hadith:
            hadith_text = "\n".join([
                f"- [{h.get('source', 'Unknown')}]: {h.get('text', '')}"
                for h in context.retrieved_hadith
            ])
            sections.append(f"HADITH:\n{hadith_text}")
        
        # Hala strategies
        if context.retrieved_strategies:
            strategies_text = "\n".join([
                f"- {s.get('title', 'Strategy')}: {s.get('description', '')}"
                for s in context.retrieved_strategies
            ])
            sections.append(f"HALA JOURNALING STRATEGIES:\n{strategies_text}")
        
        return "\n\n".join(sections) if sections else "No specific context available."
