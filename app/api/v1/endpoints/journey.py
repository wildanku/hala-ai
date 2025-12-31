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
    pipeline: PipelineOrchestrator = Depends(get_pipeline),
):
    """
    Validate user input without generating a journey.
    
    Useful for pre-validation before the full generation process.
    Only runs layers 1-3 (sanitization, semantic, safety).
    """
    # For now, just run the full pipeline
    # TODO: Add a validation-only mode to the pipeline
    result = await pipeline.execute(
        raw_input=request.prompt,
        user_id=request.user_id,
        session_id=request.session_id,
        language=request.language,
    )
    
    return {
        "is_valid": result["status"] == "success",
        "detected_scope": result.get("meta", {}).get("detected_scope"),
        "semantic_scores": result.get("meta", {}).get("semantic_scores"),
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
