"""
Layer 3: Safety & Ethical Guardrails
Ensures the AI operates within ethical and Islamic boundaries.
"""

import re
import time
from typing import Optional
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult


# Patterns indicating potential self-harm or crisis
CRISIS_PATTERNS = [
    r"\b(bunuh\s*diri|suicide|kill\s*myself|end\s*my\s*life)\b",
    r"\b(mau\s*mati|want\s*to\s*die|ingin\s*mati)\b",
    r"\b(self[\s-]*harm|melukai\s*diri)\b",
    r"\b(tidak\s*ada\s*harapan|no\s*hope|hopeless)\b",
    r"\b(lebih\s*baik\s*mati|better\s*off\s*dead)\b",
]

# Patterns indicating violent intent
VIOLENCE_PATTERNS = [
    r"\b(kill|murder|membunuh|bunuh)\s+(someone|orang|people)\b",
    r"\b(harm|hurt|menyakiti)\s+(others|orang\s*lain)\b",
    r"\b(terrorism|teroris|jihad\s*qital)\b",
    r"\b(weapons|senjata|bomb|bom)\b",
]

# Topics explicitly against Islamic values
HARAM_PATTERNS = [
    r"\b(gambling|judi|taruhan|bet|casino)\b",
    r"\b(alcohol|alkohol|miras|wine|beer|vodka|whiskey)\b",
    r"\b(riba|usury|interest\s*loan)\b",
    r"\b(zina|fornication|adultery|prostitut)\b",
    r"\b(drugs|narkoba|ganja|cocaine|heroin)\b",
    r"\b(lgbt|gay|lesbian|homosexual)\s*(relationship|marriage|nikah)\b",
    r"\b(black\s*magic|sihir|santet|dukun)\b",
]

# Crisis resources to provide
CRISIS_RESOURCES = {
    "id": {
        "hotline": "119 ext 8 (Into The Light Indonesia)",
        "website": "https://www.intothelightid.org/",
        "message": "Jika kamu sedang dalam kesulitan, tolong hubungi bantuan profesional.",
    },
    "en": {
        "hotline": "119 ext 8 (Into The Light Indonesia)",
        "website": "https://www.intothelightid.org/",
        "message": "If you're struggling, please reach out to professional help.",
    },
}


class SafetyGuardrailsLayer(PipelineLayer):
    """
    Layer 3: Safety and ethical guardrails.
    
    Detects and handles:
    - Self-harm / crisis situations
    - Violent intent
    - Topics against Islamic values
    """
    
    def __init__(
        self,
        enable_crisis_detection: bool = True,
        enable_violence_detection: bool = True,
        enable_haram_detection: bool = True,
    ):
        self._enable_crisis = enable_crisis_detection
        self._enable_violence = enable_violence_detection
        self._enable_haram = enable_haram_detection
        
        # Compile regex patterns
        self._crisis_regex = re.compile(
            "|".join(CRISIS_PATTERNS), re.IGNORECASE
        ) if enable_crisis_detection else None
        
        self._violence_regex = re.compile(
            "|".join(VIOLENCE_PATTERNS), re.IGNORECASE
        ) if enable_violence_detection else None
        
        self._haram_regex = re.compile(
            "|".join(HARAM_PATTERNS), re.IGNORECASE
        ) if enable_haram_detection else None
    
    @property
    def layer_name(self) -> str:
        return "safety_guardrails"
    
    @property
    def layer_order(self) -> int:
        return 3
    
    async def process(self, context: PipelineContext) -> PipelineResult:
        start_time = time.perf_counter()
        
        text = context.processed_input
        detected_flags = []
        
        # Check for crisis/self-harm content
        if self._crisis_regex and self._crisis_regex.search(text):
            detected_flags.append("CRISIS_DETECTED")
            context.safety_flags = detected_flags
            
            # Return special crisis response with resources
            resources = CRISIS_RESOURCES.get(context.language, CRISIS_RESOURCES["en"])
            return self._create_rejection_result(
                error_code="SAFETY_VIOLATION",
                message_id=f"{resources['message']} Hotline: {resources['hotline']}",
                message_en=f"{CRISIS_RESOURCES['en']['message']} Hotline: {resources['hotline']}",
                suggested_action=f"Please contact: {resources['hotline']} or visit {resources['website']}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Check for violent content
        if self._violence_regex and self._violence_regex.search(text):
            detected_flags.append("VIOLENCE_DETECTED")
            context.safety_flags = detected_flags
            
            return self._create_rejection_result(
                error_code="SAFETY_VIOLATION",
                message_id="Permintaan ini tidak dapat diproses karena mengandung konten kekerasan.",
                message_en="This request cannot be processed as it contains violent content.",
                suggested_action="Hala Journal is here to help with positive growth and spiritual guidance.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Check for haram topics
        if self._haram_regex and self._haram_regex.search(text):
            detected_flags.append("HARAM_TOPIC_DETECTED")
            context.safety_flags = detected_flags
            
            return self._create_rejection_result(
                error_code="SAFETY_VIOLATION",
                message_id="Maaf, topik ini bertentangan dengan nilai-nilai Islam yang kami anut.",
                message_en="Sorry, this topic conflicts with the Islamic values we uphold.",
                suggested_action="Try asking about halal alternatives or how to overcome such challenges.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        execution_time = (time.perf_counter() - start_time) * 1000
        context.layer_timings[self.layer_name] = execution_time
        context.safety_flags = detected_flags  # Empty list means all clear
        
        return self._create_success_result(
            message="Safety checks passed",
            execution_time_ms=execution_time,
        )
