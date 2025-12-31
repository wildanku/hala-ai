"""
Pipeline Orchestrator
Coordinates the execution of all pipeline layers in sequence.
"""

import time
from typing import Optional, Any
from app.pipelines.base import (
    PipelineLayer,
    PipelineContext,
    PipelineResult,
    LayerStatus,
)
from app.core.exceptions import HalaAIException
from app.core.responses import ErrorCode


class PipelineOrchestrator:
    """
    Orchestrates the multi-layer pipeline execution.
    
    Executes layers in order and short-circuits on failures.
    Provides hooks for monitoring, logging, and analytics.
    """
    
    def __init__(self):
        self._layers: list[PipelineLayer] = []
        self._on_layer_complete: Optional[callable] = None
        self._on_pipeline_complete: Optional[callable] = None
    
    def register_layer(self, layer: PipelineLayer) -> "PipelineOrchestrator":
        """
        Register a pipeline layer.
        Layers are sorted by their order property on execution.
        
        Returns self for method chaining.
        """
        self._layers.append(layer)
        return self
    
    def register_layers(self, layers: list[PipelineLayer]) -> "PipelineOrchestrator":
        """Register multiple layers at once."""
        for layer in layers:
            self._layers.append(layer)
        return self
    
    def on_layer_complete(self, callback: callable) -> "PipelineOrchestrator":
        """Set callback for when each layer completes (for monitoring)."""
        self._on_layer_complete = callback
        return self
    
    def on_pipeline_complete(self, callback: callable) -> "PipelineOrchestrator":
        """Set callback for when entire pipeline completes."""
        self._on_pipeline_complete = callback
        return self
    
    async def execute(
        self,
        raw_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        language: str = "id",
    ) -> dict[str, Any]:
        """
        Execute the full pipeline.
        
        Args:
            raw_input: The user's raw input text
            user_id: Optional user identifier
            session_id: Optional session identifier
            language: Language code (id/en)
            
        Returns:
            dict containing either success data or error response
        """
        pipeline_start = time.perf_counter()
        
        # Create pipeline context
        context = PipelineContext(
            raw_input=raw_input,
            user_id=user_id,
            session_id=session_id,
            language=language,
        )
        
        # Sort layers by order
        sorted_layers = sorted(self._layers, key=lambda l: l.layer_order)
        
        # Execute layers in sequence
        layer_results: list[PipelineResult] = []
        
        for layer in sorted_layers:
            result = await layer.process(context)
            layer_results.append(result)
            
            # Call monitoring callback if set
            if self._on_layer_complete:
                await self._on_layer_complete(layer, result, context)
            
            # Short-circuit on rejection or error
            if result.status in (LayerStatus.REJECTED, LayerStatus.ERROR):
                return self._build_error_response(result, context, pipeline_start)
        
        # All layers passed - build success response
        total_time = (time.perf_counter() - pipeline_start) * 1000
        
        response = self._build_success_response(context, layer_results, total_time)
        
        # Call pipeline complete callback if set
        if self._on_pipeline_complete:
            await self._on_pipeline_complete(response, context)
        
        return response
    
    def _build_error_response(
        self,
        result: PipelineResult,
        context: PipelineContext,
        start_time: float,
    ) -> dict[str, Any]:
        """Build standardized error response."""
        return {
            "status": "error",
            "code": result.error_code or "INTERNAL_ERROR",
            "message": {
                "id": result.message_id or result.message,
                "en": result.message_en or result.message,
            },
            "suggested_action": result.suggested_action,
            "meta": {
                "failed_at_layer": result.layer_name,
                "total_time_ms": (time.perf_counter() - start_time) * 1000,
                "layer_timings": context.layer_timings,
            },
        }
    
    def _build_success_response(
        self,
        context: PipelineContext,
        layer_results: list[PipelineResult],
        total_time: float,
    ) -> dict[str, Any]:
        """Build success response with LLM output."""
        return {
            "status": "success",
            "data": context.llm_response,
            "meta": {
                "detected_scope": context.detected_scope,
                "semantic_scores": context.semantic_scores,
                "documents_retrieved": len(context.retrieved_documents),
                "llm_provider": context.llm_provider_used,
                "total_time_ms": total_time,
                "layer_timings": context.layer_timings,
            },
        }
    
    def get_registered_layers(self) -> list[str]:
        """Get list of registered layer names."""
        return [layer.layer_name for layer in self._layers]
