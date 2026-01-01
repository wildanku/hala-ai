"""
Journey API Schemas
Pydantic models for request/response validation.
"""

from typing import Any, Optional, List
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


class BilingualVerse(BaseModel):
    """Verse with Arabic, Indonesian, and English translations."""
    
    ar: Optional[str] = Field(None, description="Arabic text")
    id: Optional[str] = Field(None, description="Indonesian translation")
    en: Optional[str] = Field(None, description="English translation")


class JourneyTask(BaseModel):
    """Single task in the journey."""
    
    day: str = Field(..., description="Day or day range (e.g., '1', '1-14')")
    type: str = Field(..., description="Task type: reflection, sadaqah, praying, gratitude, dhikr, quran, habit_break, action, kindness, self_care, physical_act")
    time: str = Field(..., description="Time: morning, afternoon, evening, night, before_sleep, at-HH:mm, anytime")
    title: BilingualMessage = Field(..., description="Task title in Indonesian and English")
    description: BilingualMessage = Field(..., description="Task description in Indonesian and English")
    verse: Optional[BilingualVerse] = Field(None, description="Optional verse reference")


class JourneyData(BaseModel):
    """The generated journey content matching the spec."""
    
    goal: str = Field(..., description="The user's goal")
    total_days: int = Field(..., description="Total journey duration (1-60 days)")
    message: Optional[str] = Field(None, description="Optional motivational message")
    introduction: BilingualMessage = Field(..., description="Journey introduction in both languages")
    goal_keyword: str = Field(..., description="Kebab-case keyword for categorization (e.g., 'career-anxiety')")
    tags: List[str] = Field(default_factory=list, description="3-5 English tags for semantic matching")
    journey: List[JourneyTask] = Field(default_factory=list, description="List of journey tasks")


# Legacy schemas for backward compatibility
class DayTask(BaseModel):
    """Single task for a day in the journey (legacy)."""
    
    title: str
    description: str
    verse_reference: Optional[str] = None
    hadith_reference: Optional[str] = None


class DayReflection(BaseModel):
    """Evening reflection for a day (legacy)."""
    
    prompt: str
    journaling_questions: list[str]


class JourneyDay(BaseModel):
    """Single day in the journey (legacy)."""
    
    day: int
    theme: str
    morning_task: DayTask
    evening_reflection: DayReflection


class JourneyMeta(BaseModel):
    """Metadata about the journey generation."""
    
    detected_scope: Optional[str] = None
    semantic_scores: Optional[dict[str, float]] = None
    documents_retrieved: Optional[int] = None
    template_used: Optional[bool] = None
    template_similarity: Optional[float] = None
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
