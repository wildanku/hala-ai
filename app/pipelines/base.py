from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class LayerStatus(str, Enum):
    """Status of pipeline layer execution."""
    
    PASSED = "passed"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class PipelineContext:
    """
    Context object passed through all pipeline layers.
    Each layer can read from and write to this context.
    """
    
    # Original input from user
    raw_input: str
    
    # Processed/cleaned input (modified by layers)
    processed_input: str = ""
    
    # User metadata (optional, from main API)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    language: str = "id"  # Default to Indonesian
    detected_language: Optional[str] = None  # Auto-detected language
    
    # Layer 2: Semantic validation results
    semantic_scores: dict[str, float] = field(default_factory=dict)
    detected_scope: Optional[str] = None
    
    # Layer 3: Safety check results
    safety_flags: list[str] = field(default_factory=list)
    
    # Layer 4: RAG retrieved context
    retrieved_documents: list[dict[str, Any]] = field(default_factory=list)
    retrieved_verses: list[dict[str, Any]] = field(default_factory=list)
    retrieved_hadith: list[dict[str, Any]] = field(default_factory=list)
    retrieved_strategies: list[dict[str, Any]] = field(default_factory=list)
    
    # Layer 5: LLM response
    llm_response: Optional[dict[str, Any]] = None
    llm_provider_used: Optional[str] = None
    
    # Metadata for tracking
    layer_timings: dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.processed_input:
            self.processed_input = self.raw_input


@dataclass
class PipelineResult:
    """Result from a single pipeline layer."""
    
    status: LayerStatus
    layer_name: str
    message: Optional[str] = None
    error_code: Optional[str] = None
    message_id: Optional[str] = None
    message_en: Optional[str] = None
    suggested_action: Optional[str] = None
    execution_time_ms: float = 0.0


class PipelineLayer(ABC):
    """
    Abstract base class for all pipeline layers.
    Implements the Template Method pattern.
    """
    
    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Unique identifier for this layer."""
        pass
    
    @property
    @abstractmethod
    def layer_order(self) -> int:
        """Execution order (1-5)."""
        pass
    
    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineResult:
        """
        Process the pipeline context.
        
        Args:
            context: The pipeline context containing all data
            
        Returns:
            PipelineResult indicating success or failure
        """
        pass
    
    def _create_success_result(
        self,
        message: str = "Layer passed successfully",
        execution_time_ms: float = 0.0,
    ) -> PipelineResult:
        """Helper to create a success result."""
        return PipelineResult(
            status=LayerStatus.PASSED,
            layer_name=self.layer_name,
            message=message,
            execution_time_ms=execution_time_ms,
        )
    
    def _create_rejection_result(
        self,
        error_code: str,
        message_id: str,
        message_en: str,
        suggested_action: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> PipelineResult:
        """Helper to create a rejection result."""
        return PipelineResult(
            status=LayerStatus.REJECTED,
            layer_name=self.layer_name,
            error_code=error_code,
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
            execution_time_ms=execution_time_ms,
        )
    
    def _create_error_result(
        self,
        message: str,
        execution_time_ms: float = 0.0,
    ) -> PipelineResult:
        """Helper to create an error result."""
        return PipelineResult(
            status=LayerStatus.ERROR,
            layer_name=self.layer_name,
            message=message,
            error_code="INTERNAL_ERROR",
            execution_time_ms=execution_time_ms,
        )
