"""
Layer 4: Context Retrieval (RAG via ChromaDB)
Grounds the AI in reality by providing verified data from our knowledge base.
"""

import time
from typing import Optional
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult
from app.core.config import settings


class RAGRetrievalLayer(PipelineLayer):
    """
    Layer 4: Retrieval-Augmented Generation context retrieval.
    
    Retrieves relevant context from ChromaDB:
    - Quran verses (Ayah)
    - Hadith
    - Hala proprietary strategies/journaling prompts
    """
    
    def __init__(
        self,
        vector_store=None,
        embedding_service=None,
        top_k: Optional[int] = None,
    ):
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._top_k = top_k or settings.rag_top_k_results
    
    @property
    def layer_name(self) -> str:
        return "rag_retrieval"
    
    @property
    def layer_order(self) -> int:
        return 4
    
    def set_vector_store(self, vector_store):
        """Set vector store (dependency injection)."""
        self._vector_store = vector_store
    
    def set_embedding_service(self, embedding_service):
        """Set embedding service (dependency injection)."""
        self._embedding_service = embedding_service
    
    async def process(self, context: PipelineContext) -> PipelineResult:
        start_time = time.perf_counter()
        
        if self._vector_store is None:
            return self._create_error_result(
                message="Vector store not initialized",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        if self._embedding_service is None:
            return self._create_error_result(
                message="Embedding service not initialized",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        try:
            # Build query combining user input and detected scope
            query = context.processed_input
            if context.detected_scope:
                query = f"{context.detected_scope}: {query}"
            
            # Get embedding for the query
            query_embedding = await self._embedding_service.get_embedding(query)
            
            # Retrieve from different collections
            # 1. Quran verses
            verses = await self._vector_store.search(
                collection_name="quran_verses",
                query_embedding=query_embedding.tolist(),
                top_k=self._top_k,
            )
            context.retrieved_verses = verses
            
            # 2. Hadith
            hadith = await self._vector_store.search(
                collection_name="hadith",
                query_embedding=query_embedding.tolist(),
                top_k=self._top_k,
            )
            context.retrieved_hadith = hadith
            
            # 3. Hala strategies (proprietary journaling prompts)
            strategies = await self._vector_store.search(
                collection_name="hala_strategies",
                query_embedding=query_embedding.tolist(),
                top_k=self._top_k,
            )
            context.retrieved_strategies = strategies
            
            # Combine all documents
            context.retrieved_documents = verses + hadith + strategies
            
            execution_time = (time.perf_counter() - start_time) * 1000
            context.layer_timings[self.layer_name] = execution_time
            
            # Check if we retrieved enough context
            if not context.retrieved_documents:
                return self._create_rejection_result(
                    error_code="RAG_FAILURE",
                    message_id="Tidak dapat menemukan konteks yang relevan untuk permintaanmu.",
                    message_en="Could not find relevant context for your request.",
                    suggested_action="Please try rephrasing your question.",
                    execution_time_ms=execution_time,
                )
            
            return self._create_success_result(
                message=f"Retrieved {len(context.retrieved_documents)} relevant documents",
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            return self._create_error_result(
                message=f"RAG retrieval error: {str(e)}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
