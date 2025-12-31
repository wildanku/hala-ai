"""
Layer 1: Deterministic Sanitization
Lightweight Python logic to filter low-quality or malicious inputs.
"""

import re
import time
from typing import Optional
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult
from app.core.config import settings


class SanitizationLayer(PipelineLayer):
    """
    Layer 1: Basic input sanitization and validation.
    
    Performs:
    - Length validation (min/max)
    - Prompt injection detection
    - Profanity filtering
    - Basic text cleaning
    """
    
    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"ignore\s+(all\s+)?above\s+instructions?",
        r"disregard\s+(all\s+)?previous",
        r"system\s*(admin|prompt|mode|override)",
        r"you\s+are\s+now\s+(a|an)",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+(to\s+be|you\s+are)",
        r"jailbreak",
        r"dan\s*mode",
        r"developer\s*mode",
        r"\[system\]",
        r"\[admin\]",
        r"<\s*script\s*>",
        r"<\s*system\s*>",
    ]
    
    # Basic profanity list (extend as needed)
    PROFANITY_WORDS = {
        # English
        "fuck", "shit", "bitch", "asshole", "bastard",
        # Indonesian
        "anjing", "bangsat", "bajingan", "keparat", "kontol", "memek",
    }
    
    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        custom_injection_patterns: Optional[list[str]] = None,
        custom_profanity_words: Optional[set[str]] = None,
    ):
        self._min_length = min_length or settings.min_input_length
        self._max_length = max_length or settings.max_input_length
        
        # Compile injection patterns for efficiency
        all_patterns = self.INJECTION_PATTERNS + (custom_injection_patterns or [])
        self._injection_regex = re.compile(
            "|".join(all_patterns),
            re.IGNORECASE
        )
        
        # Merge profanity words
        self._profanity_words = self.PROFANITY_WORDS.union(
            custom_profanity_words or set()
        )
    
    @property
    def layer_name(self) -> str:
        return "sanitization"
    
    @property
    def layer_order(self) -> int:
        return 1
    
    async def process(self, context: PipelineContext) -> PipelineResult:
        start_time = time.perf_counter()
        
        text = context.raw_input.strip()
        
        # Check minimum length
        if len(text) < self._min_length:
            return self._create_rejection_result(
                error_code="VALIDATION_ERROR",
                message_id=f"Input terlalu pendek. Minimal {self._min_length} karakter.",
                message_en=f"Input too short. Minimum {self._min_length} characters required.",
                suggested_action="Please provide more details about your question.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Check maximum length
        if len(text) > self._max_length:
            return self._create_rejection_result(
                error_code="VALIDATION_ERROR",
                message_id=f"Input terlalu panjang. Maksimal {self._max_length} karakter.",
                message_en=f"Input too long. Maximum {self._max_length} characters allowed.",
                suggested_action="Please shorten your question to be more concise.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Check for prompt injection
        if self._injection_regex.search(text):
            return self._create_rejection_result(
                error_code="INJECTION_DETECTED",
                message_id="Terdeteksi pola input yang tidak diizinkan.",
                message_en="Disallowed input pattern detected.",
                suggested_action="Please provide a genuine question without special instructions.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Check for profanity
        words = set(re.findall(r'\b\w+\b', text.lower()))
        found_profanity = words.intersection(self._profanity_words)
        if found_profanity:
            return self._create_rejection_result(
                error_code="VALIDATION_ERROR",
                message_id="Input mengandung kata-kata yang tidak pantas.",
                message_en="Input contains inappropriate language.",
                suggested_action="Please rephrase your question using appropriate language.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Clean and normalize the text
        cleaned_text = self._clean_text(text)
        context.processed_input = cleaned_text
        
        execution_time = (time.perf_counter() - start_time) * 1000
        context.layer_timings[self.layer_name] = execution_time
        
        return self._create_success_result(
            message="Input sanitization passed",
            execution_time_ms=execution_time,
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
