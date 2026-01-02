"""
Journey Generation Endpoints
Main endpoint for generating spiritual/productivity journeys using Hybrid RAG.
"""

import json
import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from app.api.deps import get_pipeline
from app.api.v1.schemas.journey import (
    JourneyRequest,
    JourneyResponse,
    JourneyErrorResponse,
)
from app.pipelines.orchestrator import PipelineOrchestrator
from app.core.exceptions import HalaAIException
from app.core.config import settings
from app.services.chromadb_service import ChromaDBService
from app.providers.gemini import GeminiProvider

router = APIRouter(prefix="/journey", tags=["Journey"])
logger = logging.getLogger(__name__)

# Template similarity threshold
TEMPLATE_HIGH_SIMILARITY_THRESHOLD = 0.85
KNOWLEDGE_RELEVANCE_THRESHOLD = 0.7

# System prompt for Gemini - Single language output based on user input
JOURNEY_PLANNER_SYSTEM_PROMPT = """You are an Islamic spiritual coach creating personalized journey plans.

DURATION GUIDELINES (choose based on goal complexity):
- Simple goals (daily habits): 7-14 days
- Medium goals (building new practices): 14-30 days  
- Complex goals (grief, addiction, major life changes): 30-60 days
- Emergency spiritual support: 1-3 days

LANGUAGE RULES:
1. DETECT the user's input language (Indonesian or English)
2. RESPOND ONLY in that same language - do NOT provide bilingual translations
3. Include the "language" field in output with value "id" for Indonesian or "en" for English

OUTPUT RULES:
1. OUTPUT: Strictly valid JSON only - no prose, no markdown, no comments
2. DURATION: Analyze the user's goal and choose appropriate duration (1-60 days)
3. SINGLE LANGUAGE: All text fields (goal, message, introduction, title, description) must be in the detected language ONLY
4. TASK TYPES: reflection, sadaqah, praying, gratitude, dhikr, quran, habit_break, action, kindness, self_care, physical_act
5. TIME: morning, afternoon, evening, night, before_sleep, at-HH:mm, anytime
6. TAGS: 3-5 descriptive English tags (tags are always in English for semantic matching)
7. TASKS: Create 1-3 tasks per day, use day ranges for recurring tasks (e.g. "1-30")
8. VERSE: For Quranic verses, include Arabic text in "ar" and translation in "translation" field (in user's language)

Return valid JSON only."""

JOURNEY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {
            "type": "string",
            "description": "Response language based on user input: 'id' or 'en'"
        },
        "goal": {"type": "string"},
        "total_days": {"type": "integer"},
        "message": {"type": "string"},
        "introduction": {
            "type": "string",
            "description": "Warm introduction in the detected user language"
        },
        "goal_keyword": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "journey": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string"},
                    "type": {"type": "string"},
                    "time": {"type": "string"},
                    "title": {
                        "type": "string",
                        "description": "Task title in user's detected language"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description in user's detected language"
                    },
                    "verse": {
                        "type": "object",
                        "nullable": True,
                        "properties": {
                            "ar": {"type": "string"},
                            "translation": {"type": "string"},
                            "source": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}


async def _validate_input_fast(request: JourneyRequest) -> Dict[str, Any]:
    """Fast validation using only sanitization layer."""
    from app.pipelines.layer1_sanitization import SanitizationLayer
    from app.pipelines.base import PipelineContext
    
    # Create context
    context = PipelineContext(
        raw_input=request.prompt,
        user_id=request.user_id,
        session_id=request.session_id,
        language=request.language,
    )
    
    # Run Layer 1: Sanitization only (for speed)
    layer1 = SanitizationLayer()
    result1 = await layer1.process(context)
    
    if result1.status != "passed":
        return {
            "is_valid": False,
            "failed_at_layer": "sanitization",
            "error_code": result1.error_code,
            "message": {
                "id": result1.message_id,
                "en": result1.message_en,
            },
            "suggested_action": result1.suggested_action,
        }
    
    # All layers passed
    return {
        "is_valid": True,
        "context": context,
        "detected_language": context.detected_language,
        "layer_timings": context.layer_timings,
    }


async def _validate_input_full(request: JourneyRequest) -> Dict[str, Any]:
    """Full validation using layers 1-3."""
    from app.pipelines.layer1_sanitization import SanitizationLayer
    from app.pipelines.layer2_semantic import SemanticValidationLayer
    from app.pipelines.layer3_safety import SafetyGuardrailsLayer
    from app.services.embedding_service import EmbeddingService
    from app.pipelines.base import PipelineContext
    
    # Create context
    context = PipelineContext(
        raw_input=request.prompt,
        user_id=request.user_id,
        session_id=request.session_id,
        language=request.language,
    )
    
    # Run Layer 1: Sanitization
    layer1 = SanitizationLayer()
    result1 = await layer1.process(context)
    
    if result1.status != "passed":
        return {
            "is_valid": False,
            "failed_at_layer": "sanitization",
            "error_code": result1.error_code,
            "message": {
                "id": result1.message_id,
                "en": result1.message_en,
            },
            "suggested_action": result1.suggested_action,
        }
    
    # Initialize embedding service for semantic validation
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    # Run Layer 2: Semantic Validation
    layer2 = SemanticValidationLayer()
    layer2.set_embedding_service(embedding_service)
    result2 = await layer2.process(context)
    
    if result2.status != "passed":
        return {
            "is_valid": False,
            "failed_at_layer": "semantic_validation",
            "error_code": result2.error_code,
            "confidence_score": list(context.semantic_scores.values())[0] if context.semantic_scores else 0.0,
            "message": {
                "id": result2.message_id,
                "en": result2.message_en,
            },
            "suggested_action": result2.suggested_action,
            "detected_scope": context.detected_scope,
        }
    
    # Run Layer 3: Safety Guardrails
    layer3 = SafetyGuardrailsLayer()
    result3 = await layer3.process(context)
    
    if result3.status != "passed":
        return {
            "is_valid": False,
            "failed_at_layer": "safety_guardrails",
            "error_code": result3.error_code,
            "message": {
                "id": result3.message_id,
                "en": result3.message_en,
            },
            "suggested_action": result3.suggested_action,
            "safety_flags": context.safety_flags,
        }
    
    # All layers passed
    return {
        "is_valid": True,
        "context": context,
        "detected_scope": context.detected_scope,
        "semantic_scores": context.semantic_scores,
        "layer_timings": context.layer_timings,
    }


def _transform_gemini_response(gemini_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Gemini response to match our expected schema."""
    
    # Map Gemini field names to our schema
    # transformed = {
    #     "goal": gemini_data.get("goal", "Spiritual Growth"),
    #     "total_days": gemini_data.get("total_days", gemini_data.get("duration_days", 30)),
    #     "message": gemini_data.get("message", ""),
    #     "introduction": gemini_data.get("introduction", {
    #         "id": "Perjalanan spiritual untuk pertumbuhan rohani",
    #         "en": "A spiritual journey for spiritual growth"
    #     }),
    #     "goal_keyword": gemini_data.get("goal_keyword", "spiritual-growth"),
    #     "tags": gemini_data.get("tags", []),
    #     "journey": gemini_data.get("journey", gemini_data.get("journey_plan", []))
    # }
    transformed = gemini_data  # Assuming Gemini response already matches our schema
    return transformed


async def _hybrid_search(
    chromadb_service: ChromaDBService,
    query: str,
    language: str = "id",
) -> Dict[str, Any]:
    """
    Perform hybrid search in ChromaDB for templates and knowledge references.
    
    Args:
        chromadb_service: ChromaDB service instance
        query: User's search query
        language: Detected user language ('id' or 'en') for filtering
    
    Returns:
        Dict with 'templates' and 'knowledge_references' lists
    """
    # Search journey templates - filtered by language
    templates = await chromadb_service.search_journey_templates(
        query=query,
        limit=3,
        active_only=True,
        language=language,
    )
    
    # Search knowledge references - filtered by language
    knowledge_refs = await chromadb_service.search_knowledge_references(
        query=query,
        limit=10,
        language=language,
    )
    
    # Also search for STORY type specifically - filtered by language
    story_refs = await chromadb_service.search_knowledge_references(
        query=query,
        limit=3,
        category="STORY",
        language=language,
    )
    
    return {
        "templates": templates,
        "knowledge_references": knowledge_refs,
        "stories": story_refs,
    }


def _format_references_for_prompt(search_results: Dict[str, Any]) -> str:
    """Format search results into a string for the LLM prompt.
    
    Uses new single-language schema where content is plain text.
    """
    references = []
    
    # Format knowledge references
    for ref in search_results.get("knowledge_references", []):
        doc = ref.get("document", {})
        distance = ref.get("distance", 1.0)
        
        # Skip low relevance references
        if distance > KNOWLEDGE_RELEVANCE_THRESHOLD:
            continue
            
        category = doc.get("category", "UNKNOWN")
        content = doc.get("content", "")  # Now plain text, single language
        title = doc.get("title", "")  # Now plain text
        source = doc.get("source", "")
        content_ar = doc.get("content_ar", "")  # Arabic for VERSE/HADITH
        
        if category == "VERSE":
            references.append(f"- Verse ({source}): {title or content}")
            if content_ar:
                references.append(f"  Arabic: {content_ar}")
        elif category == "HADITH":
            references.append(f"- Hadith ({source}): {title or content}")
            if content_ar:
                references.append(f"  Arabic: {content_ar}")
        elif category == "DOA":
            references.append(f"- Doa: {title or content}")
        elif category == "STRATEGY":
            references.append(f"- Strategy: {title or content}")
        elif category == "STORY":
            references.append(f"- Story/Wisdom: {title or content}")
    
    # Ensure at least one story is included
    story_added = any("Story/Wisdom" in r for r in references)
    if not story_added:
        for story in search_results.get("stories", []):
            doc = story.get("document", {})
            title = doc.get("title", "")
            content = doc.get("content", "")
            if title or content:
                references.append(f"- Story/Wisdom: {title or content}")
                break
    
    return "\n".join(references) if references else "(No specific references found - use your knowledge as an Islamic life coach)"


def _build_user_prompt(
    user_input: str,
    references: str,
    template: Optional[Dict] = None,
    language: str = "id",
) -> str:
    """Build the user prompt for journey generation with single-language output."""
    
    language_name = "Indonesian" if language == "id" else "English"
    
    return f"""USER GOAL: {user_input}
DETECTED LANGUAGE: {language_name} ({language})

REFERENCES FROM DATABASE:
{references if references else "(No specific references - use your Islamic knowledge)"}

INSTRUCTIONS:
1. Respond ONLY in {language_name} - do NOT provide translations
2. Analyze the user's goal and determine the appropriate journey duration (1-60 days)
3. For simple habits: 7-14 days
4. For building practices: 14-30 days
5. For grief/addiction/major changes: 30-60 days
6. Create meaningful tasks with variety
7. Tags must always be in English (for database matching)

Output this exact JSON structure:
{{
  "language": "{language}",
  "goal": "<restate user goal in {language_name}>",
  "total_days": <number between 1-60 based on goal complexity>,
  "message": "<encouraging message in {language_name}>",
  "introduction": "<warm introduction in {language_name}>",
  "goal_keyword": "<kebab-case-keyword>",
  "tags": ["tag1", "tag2", "tag3"],
  "journey": [
    {{
      "day": "1" or "1-7" for recurring,
      "type": "<task type>",
      "time": "<time of day>",
      "title": "<title in {language_name}>",
      "description": "<description in {language_name}>",
      "verse": {{
        "ar": "<Arabic text if applicable>",
        "translation": "<translation in {language_name}>",
        "source": "<source reference e.g. QS. Al-Baqarah: 286>"
      }}
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation. All text content must be in {language_name} only."""


@router.post(
    "/generate",
    response_model=JourneyResponse,
    responses={
        400: {"model": JourneyErrorResponse, "description": "Validation or scope error"},
        422: {"model": JourneyErrorResponse, "description": "Safety violation"},
        500: {"model": JourneyErrorResponse, "description": "Internal error"},
    },
)
async def generate_journey(request: JourneyRequest):
    """
    Generate a personalized spiritual/productivity journey using Hybrid RAG.
    
    This endpoint follows a Hybrid RAG approach:
    1. Analyze & Guard - Validate input for safety and scope
    2. Hybrid Search - Search journey_templates and knowledge_references in ChromaDB
    3. Decide Route:
       - If high-similarity template (>0.85) exists: Use it as base, personalize with Gemini
       - If no template exists: Create from scratch using knowledge_references
    4. Enrich - Include at least one Story/Wisdom for emotional depth
    5. Output - Return JSON matching Journey schema
    """
    start_time = time.perf_counter()
    
    try:
        # Step 1: Full validation (sanitization, semantic, safety) - BEFORE expensive LLM calls
        validation_result = await _validate_input_full(request)
        
        if not validation_result.get("is_valid"):
            status_code = _get_status_code(validation_result.get("error_code"))
            raise HTTPException(
                status_code=status_code,
                detail={
                    "status": "error",
                    "code": validation_result.get("error_code"),
                    "message": validation_result.get("message"),
                    "suggested_action": validation_result.get("suggested_action"),
                },
            )
        
        # Get detected language from validation
        detected_language = validation_result.get("context").detected_language if validation_result.get("context") else request.language
        if hasattr(detected_language, 'value'):
            detected_language = detected_language.value
        
        logger.info(f"Validation passed. Detected language: {detected_language}, Scope: {validation_result.get('detected_scope')}")
        
        # Step 2: Initialize ChromaDB and perform hybrid search with language filter
        chromadb_service = ChromaDBService(persist_directory=settings.chroma_persist_directory)
        await chromadb_service.connect()
        
        # Search with language filter to get matching content
        search_results = await _hybrid_search(
            chromadb_service, 
            request.prompt,
            language=detected_language,
        )
        
        # Step 3: Decide route based on template similarity AND language match
        templates = search_results.get("templates", [])
        best_template = None
        template_similarity = 0.0
        
        if templates:
            best_template_result = templates[0]
            # ChromaDB distance: lower is more similar (0 = exact match)
            # Convert to similarity score (1 - distance)
            distance = best_template_result.get("distance", 1.0)
            template_similarity = 1.0 - distance
            
            # Check if template language matches user language
            template_language = best_template_result.get("metadata", {}).get("language", "id")
            
            if template_similarity >= TEMPLATE_HIGH_SIMILARITY_THRESHOLD:
                if template_language == detected_language:
                    best_template = best_template_result
                    logger.info(f"Using template with similarity {template_similarity:.2f} (language: {template_language})")
                else:
                    # Template found but language doesn't match - generate new journey
                    logger.info(f"Template found (similarity: {template_similarity:.2f}) but language mismatch: template={template_language}, user={detected_language}. Generating new journey.")
                    best_template = None
            else:
                logger.info(f"No high-similarity template found (best: {template_similarity:.2f})")
        
        # Step 4: Format references for prompt
        references = _format_references_for_prompt(search_results)
        
        # Step 5: Build prompt and generate with Gemini using detected language
        user_prompt = _build_user_prompt(
            user_input=request.prompt,
            references=references,
            template=best_template,
            language=detected_language,
        )
        
        # Initialize Gemini provider
        gemini = GeminiProvider()
        
        try:
            gemini_response = await gemini.generate(
                system_prompt=JOURNEY_PLANNER_SYSTEM_PROMPT,
                user_message=user_prompt,
                response_format="json",
                temperature=0.3,  # Lower temperature for more predictable JSON
                max_tokens=4096,  # Reduced to prevent truncation
            )
            
            # Extract journey data from Gemini response
            raw_journey_data = gemini_response if isinstance(gemini_response, dict) else {}
            
            # Transform to our expected schema
            journey_data = _transform_gemini_response(raw_journey_data)
            
            # Validate that we have journey tasks
            tasks = journey_data.get('journey', [])
            if not tasks or len(tasks) == 0:
                logger.warning("No journey tasks generated, adding default task")
                journey_data['journey'] = [
                    {
                        "day": "1",
                        "type": "reflection",
                        "time": "morning",
                        "title": {
                            "id": "Refleksi Spiritual",
                            "en": "Spiritual Reflection"
                        },
                        "description": {
                            "id": "Luangkan waktu untuk merefleksikan perjalanan spiritual Anda.",
                            "en": "Take time to reflect on your spiritual journey."
                        }
                    }
                ]
                journey_data['total_days'] = 1
            
            logger.info(f"Generated journey with {len(journey_data.get('journey', []))} tasks")
            
        except Exception as llm_error:
            logger.error(f"Gemini generation failed: {str(llm_error)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "code": "LLM_FAILURE",
                    "message": {
                        "id": "Gagal menghasilkan perjalanan. Silakan coba lagi.",
                        "en": "Failed to generate journey. Please try again.",
                    },
                    "suggested_action": "Please try again in a few moments.",
                },
            )
        
        # Calculate timing
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Build response
        return {
            "status": "success",
            "data": journey_data,
            "meta": {
                "detected_scope": validation_result.get("detected_scope"),
                "semantic_scores": validation_result.get("semantic_scores"),
                "documents_retrieved": len(search_results.get("knowledge_references", [])),
                "template_used": best_template is not None,
                "template_similarity": template_similarity if best_template else None,
                "llm_provider": "gemini",
                "total_time_ms": total_time_ms,
                "layer_timings": validation_result.get("layer_timings"),
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Journey generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": {
                    "id": "Terjadi kesalahan internal. Silakan coba lagi.",
                    "en": "An internal error occurred. Please try again.",
                },
                "suggested_action": "Please try again in a few moments.",
            },
        )


@router.post("/validate")
async def validate_input(
    request: JourneyRequest,
    fast: bool = False,
):
    """
    Validate user input without generating a journey.
    
    Useful for pre-validation before the full generation process.
    Runs layers 1-3 (sanitization, semantic, safety) only.
    
    Args:
        request: Journey request with prompt and metadata
        fast: If True, only runs sanitization layer for sub-second validation
    """
    try:
        # Fast mode: return after sanitization only
        if fast:
            validation_result = await _validate_input_fast(request)
            if not validation_result.get("is_valid"):
                return validation_result
            
            return {
                "is_valid": True,
                "fast_mode": True,
                "detected_language": validation_result.get("detected_language"),
                "layer_timings": validation_result.get("layer_timings"),
                "message": "Fast validation passed (sanitization only)"
            }
        
        # Full mode: continue with all validation layers
        validation_result = await _validate_input_full(request)
        
        if not validation_result.get("is_valid"):
            return validation_result
        
        return {
            "is_valid": True,
            "confidence_score": validation_result.get("semantic_scores", {}).get("spiritual", 0.0) if validation_result.get("semantic_scores") else 0.0,
            "detected_scope": validation_result.get("detected_scope"),
            "semantic_scores": validation_result.get("semantic_scores"),
            "layer_timings": validation_result.get("layer_timings"),
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "failed_at_layer": "internal_error",
            "error_code": "INTERNAL_ERROR",
            "message": {
                "id": f"Terjadi kesalahan internal: {str(e)}",
                "en": f"Internal error occurred: {str(e)}",
            },
        }


@router.post("/validate/benchmark")
async def benchmark_validation(request: JourneyRequest):
    """
    Benchmark validation performance for optimization.
    
    Tests different validation modes to compare speed.
    """
    from app.pipelines.layer1_sanitization import SanitizationLayer
    from app.pipelines.layer2_semantic import SemanticValidationLayer
    from app.services.embedding_service import EmbeddingService
    from app.pipelines.base import PipelineContext
    
    results = {}
    
    # Test sanitization only
    start_time = time.perf_counter()
    context = PipelineContext(
        raw_input=request.prompt,
        language=request.language,
    )
    layer1 = SanitizationLayer()
    await layer1.process(context)
    sanitization_time = (time.perf_counter() - start_time) * 1000
    results["sanitization_only_ms"] = sanitization_time
    
    # Test with embedding initialization
    start_time = time.perf_counter()
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    init_time = (time.perf_counter() - start_time) * 1000
    results["embedding_init_ms"] = init_time
    
    # Test semantic validation
    start_time = time.perf_counter()
    layer2 = SemanticValidationLayer()
    layer2.set_embedding_service(embedding_service)
    await layer2.process(context)
    semantic_time = (time.perf_counter() - start_time) * 1000
    results["semantic_validation_ms"] = semantic_time
    
    results["total_ms"] = sanitization_time + init_time + semantic_time
    results["prompt_length"] = len(request.prompt)
    
    return {
        "benchmark_results": results,
        "recommendations": {
            "fast_mode": "Use ?fast=true for sub-second validation",
            "full_mode": "Full validation takes longer but provides scope detection",
            "optimization": "First request slower due to model loading, subsequent faster"
        }
    }


def _get_status_code(error_code: Optional[str]) -> int:
    """Map error codes to HTTP status codes."""
    mapping = {
        "INJECTION_DETECTED": 400,
        "VALIDATION_ERROR": 400,
        "OUT_OF_SCOPE": 400,
        "SAFETY_VIOLATION": 422,
        "RAG_FAILURE": 500,
        "LLM_FAILURE": 500,
        "PROVIDER_NOT_FOUND": 500,
        "INTERNAL_ERROR": 500,
    }
    return mapping.get(error_code, 500)
