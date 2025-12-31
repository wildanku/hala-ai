"""
Journey API Schemas
Pydantic models for request/response validation.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class LanguageCode(str, Enum):
    """Supported languages."""
    
    INDONESIAN = "id"
    ENGLISH = "en"


class JourneyRequest(BaseModel):
    """Request schema for journey generation."""
    
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="User's request for journey generation",
        json_schema_extra={
            "example": "I want to improve my morning prayer routine and feel more connected to Allah"
        },
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user identifier from main API",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session identifier for tracking",
    )
    language: LanguageCode = Field(
        LanguageCode.INDONESIAN,
        description="Response language preference",
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Saya ingin meningkatkan kebiasaan sholat tahajud",
                    "language": "id",
                },
                {
                    "prompt": "I want to develop better focus during prayers",
                    "language": "en",
                    "user_id": "user-123",
                },
            ]
        }
    }


class BilingualMessage(BaseModel):
    """Bilingual message (Indonesian & English)."""
    
    id: str = Field(..., description="Indonesian message")
    en: str = Field(..., description="English message")


class DayTask(BaseModel):
    """Single task for a day in the journey."""
    
    title: str
    description: str
    verse_reference: Optional[str] = None
    hadith_reference: Optional[str] = None


class DayReflection(BaseModel):
    """Evening reflection for a day."""
    
    prompt: str
    journaling_questions: list[str]


class JourneyDay(BaseModel):
    """Single day in the journey."""
    
    day: int
    theme: str
    morning_task: DayTask
    evening_reflection: DayReflection


class JourneyData(BaseModel):
    """The generated journey content."""
    
    journey_title: str
    journey_description: str
    scope: str
    days: list[JourneyDay]
    sources_used: dict[str, list[str]]


class JourneyMeta(BaseModel):
    """Metadata about the journey generation."""
    
    detected_scope: Optional[str] = None
    semantic_scores: Optional[dict[str, float]] = None
    documents_retrieved: Optional[int] = None
    llm_provider: Optional[str] = None
    total_time_ms: Optional[float] = None
    layer_timings: Optional[dict[str, float]] = None


class JourneyResponse(BaseModel):
    """Successful journey generation response."""
    
    status: str = "success"
    data: Optional[dict[str, Any]] = None  # JourneyData once generated
    meta: Optional[JourneyMeta] = None


class JourneyErrorResponse(BaseModel):
    """Error response for journey generation."""
    
    status: str = "error"
    code: str = Field(
        ...,
        description="Error code: OUT_OF_SCOPE, INJECTION_DETECTED, SAFETY_VIOLATION, RAG_FAILURE, LLM_FAILURE",
    )
    message: BilingualMessage
    suggested_action: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
