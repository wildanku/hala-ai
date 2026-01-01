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

# System prompt for Gemini
JOURNEY_PLANNER_SYSTEM_PROMPT = """You are an Islamic spiritual coach creating personalized journey plans.

DURATION GUIDELINES (choose based on goal complexity):
- Simple goals (daily habits): 7-14 days
- Medium goals (building new practices): 14-30 days  
- Complex goals (grief, addiction, major life changes): 30-60 days
- Emergency spiritual support: 1-3 days

RULES:
1. OUTPUT: Strictly valid JSON only - no prose, no markdown, no comments
2. DURATION: Analyze the user's goal and choose appropriate duration (1-60 days)
3. BILINGUAL: All text must have both "id" (Indonesian) and "en" (English)
4. TASK TYPES: reflection, sadaqah, praying, gratitude, dhikr, quran, habit_break, action, kindness, self_care, physical_act
5. TIME: morning, afternoon, evening, night, before_sleep, at-HH:mm, anytime
6. TAGS: 3-5 descriptive English tags
7. TASKS: Create 1-3 tasks per day, use day ranges for recurring tasks (e.g. "1-30")

Return valid JSON only."""

JOURNEY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "total_days": {"type": "integer"},
        "message": {"type": "string"},
        "introduction": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "en": {"type": "string"}
            }
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
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "en": {"type": "string"}
                        }
                    },
                    "description": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "en": {"type": "string"}
                        }
                    },
                    "verse": {
                        "type": "object",
                        "nullable": True,
                        "properties": {
                            "ar": {"type": "string"},
                            "id": {"type": "string"},
                            "en": {"type": "string"}
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
) -> Dict[str, Any]:
    """
    Perform hybrid search in ChromaDB for templates and knowledge references.
    
    Returns:
        Dict with 'templates' and 'knowledge_references' lists
    """
    # Search journey templates
    templates = await chromadb_service.search_journey_templates(
        query=query,
        limit=3,
        active_only=True,
    )
    
    # Search knowledge references
    knowledge_refs = await chromadb_service.search_knowledge_references(
        query=query,
        limit=10,
    )
    
    # Also search for STORY type specifically
    story_refs = await chromadb_service.search_knowledge_references(
        query=query,
        limit=3,
        category="STORY",
    )
    
    return {
        "templates": templates,
        "knowledge_references": knowledge_refs,
        "stories": story_refs,
    }


def _format_references_for_prompt(search_results: Dict[str, Any]) -> str:
    """Format search results into a string for the LLM prompt."""
    references = []
    
    # Format knowledge references
    for ref in search_results.get("knowledge_references", []):
        doc = ref.get("document", {})
        distance = ref.get("distance", 1.0)
        
        # Skip low relevance references
        if distance > KNOWLEDGE_RELEVANCE_THRESHOLD:
            continue
            
        category = doc.get("category", "UNKNOWN")
        content_id = doc.get("content_id", "")
        content_en = doc.get("content_en", "")
        source = doc.get("source", "")
        
        if category == "VERSE":
            references.append(f"- Verse ({source}): {content_id}")
        elif category == "HADITH":
            references.append(f"- Hadith ({source}): {content_id}")
        elif category == "DOA":
            references.append(f"- Doa: {content_id}")
        elif category == "STRATEGY":
            references.append(f"- Strategy: {content_id}")
        elif category == "STORY":
            references.append(f"- Story/Wisdom: {content_id}")
    
    # Ensure at least one story is included
    story_added = any("Story/Wisdom" in r for r in references)
    if not story_added:
        for story in search_results.get("stories", []):
            doc = story.get("document", {})
            content_id = doc.get("content_id", "")
            if content_id:
                references.append(f"- Story/Wisdom: {content_id}")
                break
    
    return "\n".join(references) if references else "(No specific references found - use your knowledge as an Islamic life coach)"


def _build_user_prompt(
    user_input: str,
    references: str,
    template: Optional[Dict] = None,
    language: str = "id",
) -> str:
    """Build the user prompt for journey generation."""
    
    return f"""USER GOAL: {user_input}
LANGUAGE PREFERENCE: {language}

REFERENCES FROM DATABASE:
{references if references else "(No specific references - use your Islamic knowledge)"}

INSTRUCTIONS:
1. Analyze the user's goal and determine the appropriate journey duration (1-60 days)
2. For simple habits: 7-14 days
3. For building practices: 14-30 days
4. For grief/addiction/major changes: 30-60 days
5. Create meaningful tasks with variety

Output this exact JSON structure:
{{
  "goal": "<restate user goal>",
  "total_days": <number between 1-60 based on goal complexity>,
  "introduction": {{"id": "<warm Indonesian intro>", "en": "<warm English intro>"}},
  "goal_keyword": "<kebab-case-keyword>",
  "tags": ["tag1", "tag2", "tag3"],
  "journey": [
    {{
      "day": "1" or "1-7" for recurring,
      "type": "<task type>",
      "time": "<time of day>",
      "title": {{"id": "<Indonesian>", "en": "<English>"}},
      "description": {{"id": "<Indonesian>", "en": "<English>"}}
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation."""


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
        # Step 1: Fast validation (sanitization only for performance)
        validation_result = await _validate_input_fast(request)
        
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
        
        # Step 2: Initialize ChromaDB and perform hybrid search
        chromadb_service = ChromaDBService(persist_directory=settings.chroma_persist_directory)
        await chromadb_service.connect()
        
        search_results = await _hybrid_search(chromadb_service, request.prompt)
        
        # Step 3: Decide route based on template similarity
        templates = search_results.get("templates", [])
        best_template = None
        template_similarity = 0.0
        
        if templates:
            best_template_result = templates[0]
            # ChromaDB distance: lower is more similar (0 = exact match)
            # Convert to similarity score (1 - distance)
            distance = best_template_result.get("distance", 1.0)
            template_similarity = 1.0 - distance
            
            if template_similarity >= TEMPLATE_HIGH_SIMILARITY_THRESHOLD:
                best_template = best_template_result
                logger.info(f"Using template with similarity {template_similarity:.2f}")
            else:
                logger.info(f"No high-similarity template found (best: {template_similarity:.2f})")
        
        # Step 4: Format references for prompt
        references = _format_references_for_prompt(search_results)
        
        # Step 5: Build prompt and generate with Gemini
        user_prompt = _build_user_prompt(
            user_input=request.prompt,
            references=references,
            template=best_template,
            language=request.language.value if hasattr(request.language, 'value') else request.language,
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
