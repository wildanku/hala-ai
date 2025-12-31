"""
Layer 2: Semantic Scope Validation
Uses Sentence-Transformers to ensure the topic aligns with platform's mission.
"""

import time
from typing import Optional
import numpy as np
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult
from app.core.config import settings


# Define official scopes with comprehensive descriptions for better semantic matching
# OFFICIAL_SCOPES = {
#     "worship": [
#         "prayer salat sholat doa ibadah quran reading tilawah",
#         "fasting ramadan puasa sunnah monday thursday",
#         "dhikr zikir remembrance allah subhanallah alhamdulillah",
#         "tahajjud night prayer qiyamul lail",
#     ],
#     "mental_health": [
#         "anxiety stress worry gelisah cemas khawatir",
#         "depression sadness sedih murung mental health",
#         "peace of mind ketenangan inner peace",
#         "emotional healing sembuh batin trauma",
#         "self-care perawatan diri istirahat",
#     ],
#     "productivity": [
#         "time management manajemen waktu produktif",
#         "focus concentration konsentrasi fokus",
#         "habits kebiasaan routine rutinitas",
#         "goals target achieve capai tujuan",
#         "discipline disiplin istiqomah consistent",
#     ],
#     "self_improvement": [
#         "personal growth pengembangan diri",
#         "learning belajar ilmu knowledge",
#         "character building akhlak moral",
#         "patience sabar grateful syukur",
#     ],
#     "relationships": [
#         "family keluarga parents orang tua",
#         "marriage nikah spouse suami istri",
#         "friendship teman persahabatan",
#         "community ummah jamaah",
#     ],
#     "spiritual_growth": [
#         "tawakkal trust in allah faith iman",
#         "taubat repentance istighfar forgiveness",
#         "sincerity ikhlas niat intention",
#         "islamic values nilai islam akidah",
#     ],
# }

OFFICIAL_SCOPES = [
    # 1. Worship, Rituals & Spiritual Roadmap (Focus: Amalan & Hajat)
    "Daily worship plan amalan harian rutin ibadah doa khusus hajat wirid zikir rezeki lancar sholawat nariyah munjiyat pintu langit salat sholat lima waktu tahajjud qiyamul lail night prayer subuh dzuhur ashar maghrib isya sunnah rawatib dhuha doa supplication dhikr zikir pagi petang remembrance of allah quran journaling tilawah recitation fasting puasa ramadan sunnah senin kamis daud zakat infaq shadaqah charity hajj umrah pilgrimage ritual spiritual roadmap journey",
    
    # 2. Mental Health, Emotional Healing & Resilience (Focus: Feelings & Inner Peace)
    "Mental health emotional healing ketenangan jiwa batin anxiety cemas gelisah khawatir worry depression sedih murung sadness stress management burnout overthinking quarter-life crisis self-care healing trauma psychological wellbeing inner peace istirahat rest relaxation mindfulness tafakkur muhasabah therapy counseling self-love forgiveness memaafkan ikhlas ridho patience sabar coping mechanism emosi stabil",
    
    # 3. Productivity, Halal Wealth & Career (Focus: "Pengen Kaya" & Halal Success)
    "Productivity wealth financial success rizki rezeki berlimpah kaya wealthy sukses muda entrepreneurship bisnis islami halal money abundance manajemen waktu amanah tanggung jawab discipline disiplin focus concentration konsentrasi habits formation kebiasaan routine rutinitas goal setting target achieve capai tujuan work-life balance remote work istiqomah consistent consistency organized planning scheduling efficiency effectiveness procrastination menunda pekerjaan karir islami islamic career professional growth",
    
    # 4. Marriage, Jodoh & Social Conduct (Focus: "Dapat Jodoh" & Relationships)
    "Marriage nikah keluarga family relationships mencari jodoh cepat dapat jodoh jodoh impian pasangan sholeh sholehah taaruf soulmate spouse suami istri husband wife parenting anak children orang tua parents family harmony relationship advice dating syari pre-marital guidance silaturahmi ukhuwah brotherhood sisterhood social conduct adab bergaul community involvement household management bakti orang tua birrul walidain lamaran khitbah persiapan nikah",
    
    # 5. Akhlaq, Identity & Personal Growth (Focus: Character Transformation)
    "Character building akhlaq akhlak self-improvement personal development pengembangan diri moral values nilai moral identity krisis identitas humility tawadhu sincerity niat intention behavior improvement attitude mindset positive thinking syukur gratitude modesty malu jujur amanah integrity bravery keberanian self-control menahan hawa nafsu mujahadah an-nafs memantaskan diri",
    
    # 6. Repentance, Recovery & Overcoming Struggles (Focus: Breaking Bad Habits)
    "Repentance taubat nasuha istighfar seeking forgiveness spiritual growth hijrah meninggalkan maksiat bad habits formation berhenti merokok addiction recovery porn addiction tawakkal trust in allah faith iman islamic values understanding islam learning agama following prophet muhammad sunnah prophetic examples overcoming fear turning back to god perbaikan perilaku"
]


class SemanticValidationLayer(PipelineLayer):
    """
    Layer 2: Semantic scope validation using sentence embeddings.
    
    Uses cosine similarity to check if user input aligns with
    official platform scopes (Worship, Mental Health, Productivity, etc.)
    """
    
    # Class-level cache for scope embeddings (shared across instances)
    _cached_scope_embeddings: Optional[list[np.ndarray]] = None
    _embeddings_lock = False  # Simple lock to prevent multiple initializations
    
    def __init__(
        self,
        embedding_service=None,
        similarity_threshold: Optional[float] = None,
    ):
        self._embedding_service = embedding_service
        self._threshold = similarity_threshold or settings.semantic_similarity_threshold
        self._scope_embeddings: Optional[list[np.ndarray]] = None
    
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
        """Pre-compute embeddings for all official scopes with caching."""
        # Use class-level cache if available
        if SemanticValidationLayer._cached_scope_embeddings is not None:
            self._scope_embeddings = SemanticValidationLayer._cached_scope_embeddings
            return
        
        # If already initializing, wait
        if SemanticValidationLayer._embeddings_lock:
            import asyncio
            while SemanticValidationLayer._embeddings_lock:
                await asyncio.sleep(0.01)
            if SemanticValidationLayer._cached_scope_embeddings is not None:
                self._scope_embeddings = SemanticValidationLayer._cached_scope_embeddings
                return
        
        if self._embedding_service is None:
            raise RuntimeError("Embedding service not initialized")
        
        # Set lock and compute embeddings
        SemanticValidationLayer._embeddings_lock = True
        try:
            # Use batch processing for faster computation
            embeddings = await self._embedding_service.get_embeddings(OFFICIAL_SCOPES)
            self._scope_embeddings = [embeddings[i] for i in range(len(OFFICIAL_SCOPES))]
            
            # Cache at class level
            SemanticValidationLayer._cached_scope_embeddings = self._scope_embeddings
        finally:
            SemanticValidationLayer._embeddings_lock = False
    
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
        max_similarity = 0.0
        best_scope_index = -1
        
        for i, scope_embedding in enumerate(self._scope_embeddings):
            similarity = self._cosine_similarity(input_embedding, scope_embedding)
            if similarity > max_similarity:
                max_similarity = similarity
                best_scope_index = i
        
        # Store scores in context (simplified for new structure)
        scope_names = ["worship", "mental_health", "productivity", "marriage_family", "character_building", "spiritual_growth"]
        context.semantic_scores = {scope_names[best_scope_index]: max_similarity}
        
        execution_time = (time.perf_counter() - start_time) * 1000
        context.layer_timings[self.layer_name] = execution_time
        
        # Check if score meets threshold
        if max_similarity < self._threshold:
            return self._create_rejection_result(
                error_code="OUT_OF_SCOPE",
                message_id="Maaf, permintaanmu berada di luar jangkauan bimbingan Hala Journal.",
                message_en="Sorry, your request is outside the scope of Hala Journal guidance.",
                suggested_action="Try asking about spiritual habits, worship, mental health, or productivity.",
                execution_time_ms=execution_time,
            )
        
        # Set detected scope
        context.detected_scope = scope_names[best_scope_index] if best_scope_index >= 0 else "general"
        
        return self._create_success_result(
            message=f"Input matched scope '{context.detected_scope}' with score {max_similarity:.3f}",
            execution_time_ms=execution_time,
        )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
