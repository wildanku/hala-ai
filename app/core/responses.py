from enum import Enum
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    
    INJECTION_DETECTED = "INJECTION_DETECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    RAG_FAILURE = "RAG_FAILURE"
    LLM_FAILURE = "LLM_FAILURE"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class BilingualMessage(BaseModel):
    """Bilingual message support (Indonesian & English)."""
    
    id: str = Field(..., description="Indonesian message")
    en: str = Field(..., description="English message")


T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    
    status: str = "success"
    data: T
    meta: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response as per spec-docs."""
    
    status: str = "error"
    code: ErrorCode
    message: BilingualMessage
    suggested_action: Optional[str] = None


def create_error_response(
    code: ErrorCode,
    message_id: str,
    message_en: str,
    suggested_action: Optional[str] = None,
) -> ErrorResponse:
    """Factory function to create standardized error response."""
    return ErrorResponse(
        code=code,
        message=BilingualMessage(id=message_id, en=message_en),
        suggested_action=suggested_action,
    )


def create_success_response(
    data: Any,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Factory function to create standardized success response."""
    response = {
        "status": "success",
        "data": data,
    }
    if meta:
        response["meta"] = meta
    return response
