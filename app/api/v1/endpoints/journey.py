"""
Journey Generation Endpoints
Main endpoint for generating spiritual/productivity journeys.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.api.deps import get_pipeline
from app.api.v1.schemas.journey import (
    JourneyRequest,
    JourneyResponse,
    JourneyErrorResponse,
)
from app.pipelines.orchestrator import PipelineOrchestrator
from app.core.exceptions import HalaAIException

router = APIRouter(prefix="/journey", tags=["Journey"])


@router.post(
    "/generate",
    response_model=JourneyResponse,
    responses={
        400: {"model": JourneyErrorResponse, "description": "Validation or scope error"},
        422: {"model": JourneyErrorResponse, "description": "Safety violation"},
        500: {"model": JourneyErrorResponse, "description": "Internal error"},
    },
)
async def generate_journey(
    request: JourneyRequest,
    pipeline: PipelineOrchestrator = Depends(get_pipeline),
):
    """
    Generate a personalized spiritual/productivity journey.
    
    This endpoint processes the user input through the 5-layer pipeline:
    1. Sanitization - Basic input validation
    2. Semantic Validation - Scope checking
    3. Safety Guardrails - Ethical checks
    4. RAG Retrieval - Knowledge base lookup
    5. LLM Inference - Journey generation
    
    Returns a structured 14-day journey with daily tasks and reflections.
    """
    try:
        result = await pipeline.execute(
            raw_input=request.prompt,
            user_id=request.user_id,
            session_id=request.session_id,
            language=request.language,
        )
        
        if result["status"] == "error":
            # Map error codes to HTTP status codes
            status_code = _get_status_code(result.get("code"))
            raise HTTPException(
                status_code=status_code,
                detail=result,
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
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
    fast: bool = False,  # Add fast mode parameter
    pipeline: PipelineOrchestrator = Depends(get_pipeline),
):
    """
    Validate user input without generating a journey.
    
    Useful for pre-validation before the full generation process.
    Runs layers 1-3 (sanitization, semantic, safety) only.
    
    Args:
        request: Journey request with prompt and metadata
        fast: If True, only runs sanitization layer for sub-second validation
    """
    from app.pipelines.layer1_sanitization import SanitizationLayer
    from app.pipelines.layer2_semantic import SemanticValidationLayer
    from app.pipelines.layer3_safety import SafetyGuardrailsLayer
    from app.services.embedding_service import EmbeddingService
    from app.pipelines.base import PipelineContext
    
    try:
        # Create context
        context = PipelineContext(
            raw_input=request.prompt,
            user_id=request.user_id,
            session_id=request.session_id,
            language=request.language,
        )
        
        # Run Layer 1: Sanitization (always runs)
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
        
        # Fast mode: return after sanitization only
        if fast:
            return {
                "is_valid": True,
                "fast_mode": True,
                "detected_language": context.detected_language,
                "layer_timings": context.layer_timings,
                "message": "Fast validation passed (sanitization only)"
            }
        
        # Full mode: continue with semantic and safety layers
        # Initialize services
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
            "confidence_score": list(context.semantic_scores.values())[0] if context.semantic_scores else 0.0,
            "detected_scope": context.detected_scope,
            "semantic_scores": context.semantic_scores,
            "layer_timings": context.layer_timings,
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
async def benchmark_validation(
    request: JourneyRequest,
):
    """
    Benchmark validation performance for optimization.
    
    Tests different validation modes to compare speed.
    """
    import time
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
