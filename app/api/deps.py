"""
Dependency Injection for FastAPI
Provides singleton instances of services and pipeline.
"""

from functools import lru_cache
from typing import Optional
from app.pipelines.orchestrator import PipelineOrchestrator
from app.pipelines.layer1_sanitization import SanitizationLayer
from app.pipelines.layer2_semantic import SemanticValidationLayer
from app.pipelines.layer3_safety import SafetyGuardrailsLayer
from app.pipelines.layer4_rag import RAGRetrievalLayer
from app.pipelines.layer5_inference import LLMInferenceLayer
from app.providers.factory import get_llm_provider
from app.services.embedding_service import EmbeddingService
from app.db.vector.chroma_store import ChromaVectorStore


# Singleton instances
_embedding_service: Optional[EmbeddingService] = None
_vector_store: Optional[ChromaVectorStore] = None
_pipeline: Optional[PipelineOrchestrator] = None


async def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        await _embedding_service.initialize()
    return _embedding_service


async def get_vector_store() -> ChromaVectorStore:
    """Get or create vector store singleton."""
    global _vector_store
    if _vector_store is None:
        embedding_service = await get_embedding_service()
        _vector_store = ChromaVectorStore(embedding_service=embedding_service)
        await _vector_store.initialize()
    return _vector_store


async def get_pipeline() -> PipelineOrchestrator:
    """
    Get or create the main pipeline orchestrator.
    Initializes all layers with their dependencies.
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    
    # Get services
    embedding_service = await get_embedding_service()
    vector_store = await get_vector_store()
    llm_provider = get_llm_provider()
    
    # Create layers
    layer1 = SanitizationLayer()
    
    layer2 = SemanticValidationLayer()
    layer2.set_embedding_service(embedding_service)
    
    layer3 = SafetyGuardrailsLayer()
    
    layer4 = RAGRetrievalLayer()
    layer4.set_embedding_service(embedding_service)
    layer4.set_vector_store(vector_store)
    
    layer5 = LLMInferenceLayer()
    layer5.set_llm_provider(llm_provider)
    
    # Create and configure pipeline
    _pipeline = PipelineOrchestrator()
    _pipeline.register_layers([layer1, layer2, layer3, layer4, layer5])
    
    return _pipeline


async def reset_pipeline() -> None:
    """Reset pipeline (useful for testing or reconfiguration)."""
    global _pipeline
    _pipeline = None


async def shutdown_services() -> None:
    """Cleanup services on shutdown."""
    global _embedding_service, _vector_store, _pipeline
    _embedding_service = None
    _vector_store = None
    _pipeline = None
