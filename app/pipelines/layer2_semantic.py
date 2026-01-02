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
    """Saya ingin meningkatkan ibadah dan amalan harian saya. Bagaimana cara menjaga konsistensi sholat lima waktu dan tahajjud?
    Saya ingin mendekatkan diri kepada Allah melalui doa, zikir, dan tilawah Al-Quran setiap hari.
    Tolong buatkan jadwal ibadah untuk meningkatkan kualitas spiritual saya termasuk puasa sunnah dan sholawat.
    I want to improve my daily worship routine including prayer, fasting, Quran recitation, and remembrance of Allah.
    Help me create a spiritual roadmap with tahajjud, dhuha prayer, morning and evening adhkar, and consistent dhikr practice.
    How can I be more consistent with my salat, sunnah prayers, and Ramadan preparation?
    Saya ingin belajar sholat dengan benar dan khusyuk. Bantu saya dengan amalan wirid dan zikir harian.""",
    
    # 2. Mental Health, Emotional Healing & Resilience (Focus: Feelings & Inner Peace)
    """Saya sedang berduka setelah kehilangan ibu saya. Ayah saya meninggal dan saya sangat sedih.
    Saya kehilangan orang yang saya sayangi dan hati saya hancur. Bagaimana cara menghadapi duka dan kesedihan ini?
    Ibu saya wafat dan saya tidak tahu harus berbuat apa. Saya merasa sangat kehilangan dan terpuruk.
    Saya merasa cemas, gelisah, dan overthinking setiap hari. Saya butuh ketenangan batin dan kedamaian jiwa.
    Saya mengalami stres berat, burnout, dan depresi. Bagaimana cara menyembuhkan trauma dan luka batin saya?
    I am grieving after losing my mother. My father passed away and I feel devastated and heartbroken.
    I lost someone I love and I don't know how to cope with this grief, loss, and bereavement.
    I struggle with anxiety, worry, stress, and mental health issues. Help me find inner peace and emotional healing.
    Saya merasa kesepian, sedih, dan butuh curhat. Hati saya berat sekali. Tolong bantu saya sembuh dari luka ini.""",
    
    # 3. Productivity, Halal Wealth & Career (Focus: "Pengen Kaya" & Halal Success)
    """Saya ingin sukses dan kaya secara halal. Bagaimana cara meningkatkan produktivitas dan rezeki saya?
    Saya ingin membangun bisnis islami dan mencapai financial freedom dengan cara yang berkah dan halal.
    Tolong bantu saya mengatur waktu, fokus pada tujuan karir, dan mengatasi kebiasaan menunda pekerjaan.
    I want to be productive, wealthy, and financially successful through halal means and hard work.
    Help me with time management, discipline, and achieving my career goals as a Muslim professional.
    I struggle with procrastination and want to be more organized, efficient, and consistent in my work and business.""",
    
    # 4. Marriage, Jodoh & Social Conduct (Focus: "Dapat Jodoh" & Relationships)
    """Saya ingin segera menikah dan mendapatkan jodoh yang sholeh atau sholehah. Bagaimana caranya?
    Saya ingin memperbaiki hubungan dengan keluarga, orang tua, suami, istri, dan anak-anak saya.
    Tolong bantu saya mempersiapkan pernikahan, taaruf, dan menjadi suami atau istri yang baik.
    I want to find a righteous spouse and get married soon. How do I prepare for marriage and taaruf?
    Help me improve my relationships with family, parents, spouse, and children.
    I want to be a better parent, maintain family harmony, and fulfill my duties to my parents (birrul walidain).""",
    
    # 5. Akhlaq, Identity & Personal Growth (Focus: Character Transformation)
    """Saya ingin memperbaiki akhlak dan menjadi pribadi yang lebih baik. Bagaimana cara mengembangkan diri?
    Saya mengalami krisis identitas dan ingin menemukan jati diri sebagai Muslim yang lebih baik.
    Tolong bantu saya menjadi lebih sabar, syukur, rendah hati, dan jujur dalam kehidupan sehari-hari.
    I want to improve my character, morals, and become a better person with good akhlaq.
    Help me develop humility, gratitude, sincerity, and self-control. I want to grow as a Muslim.
    I struggle with my attitude and mindset. How can I build integrity, patience, and positive thinking?""",
    
    # 6. Repentance, Recovery & Overcoming Struggles (Focus: Breaking Bad Habits)
    """Saya ingin bertaubat dan meninggalkan kebiasaan buruk. Bagaimana cara hijrah dan memperbaiki diri?
    Saya kecanduan dan ingin berhenti. Tolong bantu saya kembali ke jalan yang benar.
    Saya ingin mendekatkan diri kepada Allah setelah banyak berbuat dosa dan maksiat.
    I want to repent and seek forgiveness from Allah. Help me overcome my bad habits and addiction.
    I want to make hijrah, leave my sinful past behind, and become a better Muslim.
    How can I strengthen my faith (iman), trust in Allah (tawakkal), and follow the Prophet's sunnah?"""
]

# Keywords that indicate genuine platform-related queries
PLATFORM_KEYWORDS = {
    # Islamic/Spiritual terms
    "islamic": ["sholat", "doa", "ibadah", "quran", "tilawah", "zikir", "dhikr", "tahajjud", "dhuha", "sunnah", "islam", "muslim", "allah", "niat", "ikhlas", "taubat", "hijrah", "iman", "tawakkal", "dosa", "maksiat", "halal", "haram", "sholeh", "sholehah", "taaruf", "nikah", "pernikahan", "jodoh", "akhlaq", "akhlak", "adab", "istighfar", "forgiveness", "prayer", "worship", "spiritual", "faith", "quran", "prophet", "sunnah", "ramadan", "fasting", "hajj"],
    
    # Mental Health & Emotions
    "mental_health": ["cemas", "gelisah", "khawatir", "worry", "anxiety", "stress", "sedih", "sad", "depression", "depresi", "trauma", "duka", "berduka", "grief", "heartbroken", "hancur", "terpuruk", "kehilangan", "meninggal", "wafat", "kesepian", "loneliness", "curhat", "burnout", "overthinking", "ketenangan", "peace", "inner", "healing", "sembuh", "batin", "jiwa"],
    
    # Productivity & Wealth
    "productivity": ["produktif", "produktivitas", "sukses", "successful", "kaya", "wealthy", "rezeki", "wealth", "bisnis", "business", "karir", "career", "kerja", "work", "entrepreneur", "waktu", "time", "fokus", "focus", "disiplin", "discipline", "kebiasaan", "habit", "tujuan", "goal", "efficient", "procrastination", "menunda"],
    
    # Relationships & Family
    "relationships": ["nikah", "menikah", "marriage", "jodoh", "pasangan", "spouse", "suami", "istri", "husband", "wife", "keluarga", "family", "orang tua", "parents", "anak", "children", "hubungan", "relationship", "taaruf", "keharmonisan", "harmony", "anak", "parenting"],
    
    # Character & Growth
    "character": ["akhlaq", "akhlak", "karakter", "character", "diri", "self", "pertumbuhan", "growth", "pengembangan", "development", "perbaikan", "improvement", "sabar", "patience", "syukur", "gratitude", "rendah hati", "humble", "jujur", "honest", "ikhlas", "sincere", "amanah", "integrity", "identitas", "identity"],
    
    # Recovery & Habits
    "recovery": ["taubat", "repentance", "hijrah", "berhenti", "stop", "kecanduan", "addiction", "maksiat", "sin", "dosa", "kebiasaan buruk", "bad habits", "memperbaiki", "improve", "kembali", "return", "jalan yang benar", "right path", "iman", "faith"]
}


class SemanticValidationLayer(PipelineLayer):
    """
    Layer 2: Semantic scope validation using sentence embeddings.
    
    Uses cosine similarity to check if user input aligns with
    official platform scopes (Worship, Mental Health, Productivity, etc.)
    """
    
    # Class-level cache for scope embeddings (shared across instances)
    _cached_scope_embeddings: Optional[list[np.ndarray]] = None
    _embeddings_lock = False  # Simple lock to prevent multiple initializations
    
    @classmethod
    def invalidate_cache(cls):
        """Invalidate cached embeddings (call when OFFICIAL_SCOPES changes)."""
        cls._cached_scope_embeddings = None
    
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
        
        # Secondary validation: check for meaningful platform-related keywords
        # This helps reject nonsense queries that happen to score high semantically
        keyword_match = self._check_keyword_relevance(context.processed_input)
        if max_similarity < 0.50 and not keyword_match:
            # If semantic score is borderline and no keywords found, reject it
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
    
    def _check_keyword_relevance(self, text: str) -> bool:
        """
        Secondary validation: check if text contains meaningful platform-related keywords.
        Returns True if at least one keyword from platform domains is found.
        """
        text_lower = text.lower()
        
        # Count keywords found across all categories
        keywords_found = 0
        for category, keywords in PLATFORM_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    keywords_found += 1
                    break  # Count once per category
        
        # Require at least one category's keywords to be present
        return keywords_found >= 1
