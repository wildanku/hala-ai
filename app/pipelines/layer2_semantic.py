"""
Layer 2: Semantic Scope Validation
Uses Sentence-Transformers to ensure the topic aligns with platform's mission.
"""

import time
from typing import Optional
import numpy as np
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult
from app.core.config import settings


# Define official scopes with representative phrases
OFFICIAL_SCOPES = {
    "worship": [
        "prayer salat sholat doa ibadah quran reading tilawah",
        "fasting ramadan puasa sunnah monday thursday",
        "dhikr zikir remembrance allah subhanallah alhamdulillah",
        "tahajjud night prayer qiyamul lail",
    ],
    "mental_health": [
        "anxiety stress worry gelisah cemas khawatir",
        "depression sadness sedih murung mental health",
        "peace of mind ketenangan inner peace",
        "emotional healing sembuh batin trauma",
        "self-care perawatan diri istirahat",
    ],
    "productivity": [
        "time management manajemen waktu produktif",
        "focus concentration konsentrasi fokus",
        "habits kebiasaan routine rutinitas",
        "goals target achieve capai tujuan",
        "discipline disiplin istiqomah consistent",
    ],
    "self_improvement": [
        "personal growth pengembangan diri",
        "learning belajar ilmu knowledge",
        "character building akhlak moral",
        "patience sabar grateful syukur",
    ],
    "relationships": [
        "family keluarga parents orang tua",
        "marriage nikah spouse suami istri",
        "friendship teman persahabatan",
        "community ummah jamaah",
    ],
    "spiritual_growth": [
        "tawakkal trust in allah faith iman",
        "taubat repentance istighfar forgiveness",
        "sincerity ikhlas niat intention",
        "islamic values nilai islam akidah",
    ],
}


class SemanticValidationLayer(PipelineLayer):
    """
    Layer 2: Semantic scope validation using sentence embeddings.
    
    Uses cosine similarity to check if user input aligns with
    official platform scopes (Worship, Mental Health, Productivity, etc.)
    """
    
    def __init__(
        self,
        embedding_service=None,
        similarity_threshold: Optional[float] = None,
    ):
        self._embedding_service = embedding_service
        self._threshold = similarity_threshold or settings.semantic_similarity_threshold
        self._scope_embeddings: Optional[dict[str, np.ndarray]] = None
    
    @property
    def layer_name(self) -> str:
        return "semantic_validation"
    
    @property
    def layer_order(self) -> int:
        return 2
    
    def set_embedding_service(self, embedding_service):
        """Set embedding service (dependency injection)."""
        self._embedding_service = embedding_service
    
    async def initialize_scope_embeddings(self):
        """Pre-compute embeddings for all official scopes."""
        if self._scope_embeddings is not None:
            return
        
        if self._embedding_service is None:
            raise RuntimeError("Embedding service not initialized")
        
        self._scope_embeddings = {}
        for scope_name, phrases in OFFICIAL_SCOPES.items():
            # Combine all phrases for this scope and get embedding
            combined_text = " ".join(phrases)
            embedding = await self._embedding_service.get_embedding(combined_text)
            self._scope_embeddings[scope_name] = embedding
    
    async def process(self, context: PipelineContext) -> PipelineResult:
        start_time = time.perf_counter()
        
        if self._embedding_service is None:
            return self._create_error_result(
                message="Embedding service not initialized",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Ensure scope embeddings are initialized
        await self.initialize_scope_embeddings()
        
        # Get embedding for user input
        input_embedding = await self._embedding_service.get_embedding(
            context.processed_input
        )
        
        # Calculate similarity with each scope
        scope_scores = {}
        for scope_name, scope_embedding in self._scope_embeddings.items():
            similarity = self._cosine_similarity(input_embedding, scope_embedding)
            scope_scores[scope_name] = float(similarity)
        
        # Store scores in context
        context.semantic_scores = scope_scores
        
        # Find best matching scope
        best_scope = max(scope_scores, key=scope_scores.get)
        best_score = scope_scores[best_scope]
        
        execution_time = (time.perf_counter() - start_time) * 1000
        context.layer_timings[self.layer_name] = execution_time
        
        # Check if score meets threshold
        if best_score < self._threshold:
            return self._create_rejection_result(
                error_code="OUT_OF_SCOPE",
                message_id="Maaf, permintaanmu berada di luar jangkauan bimbingan Hala Journal.",
                message_en="Sorry, your request is outside the scope of Hala Journal guidance.",
                suggested_action="Try asking about spiritual habits, worship, mental health, or productivity.",
                execution_time_ms=execution_time,
            )
        
        # Set detected scope
        context.detected_scope = best_scope
        
        return self._create_success_result(
            message=f"Input matched scope '{best_scope}' with score {best_score:.3f}",
            execution_time_ms=execution_time,
        )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
