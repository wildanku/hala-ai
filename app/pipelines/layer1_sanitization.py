"""
Layer 1: Deterministic Sanitization
Lightweight Python logic to filter low-quality or malicious inputs.
"""

import re
import time
from typing import Optional
from app.pipelines.base import PipelineLayer, PipelineContext, PipelineResult
from app.core.config import settings
import string
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException


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
    
    # Supported languages (language codes)
    SUPPORTED_LANGUAGES = {"id", "en"}  # Indonesian and English
    
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
        
        # Check language support (auto-detect language) - BEFORE random check
        detected_language = self._detect_language(text)
        if detected_language and detected_language not in self.SUPPORTED_LANGUAGES:
            language_names = {"id": "Indonesian", "en": "English"}
            supported_list = ", ".join([language_names.get(lang, lang.upper()) for lang in self.SUPPORTED_LANGUAGES])
            return self._create_rejection_result(
                error_code="LANGUAGE_NOT_SUPPORTED",
                message_id=f"Bahasa yang terdeteksi ({detected_language.upper()}) tidak didukung. Saat ini kami hanya mendukung: {supported_list}.",
                message_en=f"Detected language ({detected_language.upper()}) is not supported. Currently we only support: {supported_list}.",
                suggested_action=f"Please rephrase your question in {supported_list}.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        # Store detected language in context for later use
        context.detected_language = detected_language or context.language
        
        # Check for random/gibberish text (only if language detection failed)
        if not detected_language and self._is_random_string(text):
            return self._create_rejection_result(
                error_code="VALIDATION_ERROR",
                message_id="Input mengandung teks acak atau tidak bermakna. Silakan berikan pertanyaan yang jelas dan bermakna.",
                message_en="Input contains random or meaningless text. Please provide a clear and meaningful question.",
                suggested_action="Rephrase your question with real words and meaningful content.",
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
    
    def _is_random_string(self, text: str) -> bool:
        """
        Detect if input is random gibberish or meaningless text.
        
        Uses heuristics:
        - Check for known languages (English, Indonesian, Arabic)
        - Check for repeated meaningless patterns
        - Analyze character distribution
        """
        text_lower = text.lower()
        
        # Common English words (sample for basic language detection)
        common_words_en = {
            'the', 'a', 'an', 'and', 'or', 'is', 'are', 'was', 'were', 'be',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
            'how', 'where', 'when', 'why', 'can', 'will', 'do', 'does', 'did',
            'have', 'has', 'should', 'would', 'could', 'my', 'your', 'his',
            'her', 'our', 'their', 'want', 'need', 'help', 'make', 'think',
            'about', 'for', 'to', 'of', 'in', 'on', 'at', 'by', 'with',
        }
        
        # Common Indonesian words
        common_words_id = {
            'saya', 'aku', 'anda', 'dia', 'kami', 'mereka', 'adalah', 'ada',
            'yang', 'untuk', 'dengan', 'dari', 'ke', 'pada', 'di', 'dan',
            'atau', 'tidak', 'ya', 'sholat', 'tahajud', 'belajar', 'ingin',
            'meningkatkan', 'kebiasaan', 'doa', 'salat', 'ibadah', 'quran',
            'diri', 'hidup', 'apa', 'berapa', 'kapan', 'dimana', 'bagaimana',
            'siapa', 'mengapa', 'bisa', 'dapat', 'perlu', 'harus', 'ingin',
        }
        
        # Split into words and normalize
        words = text.split()
        if not words:
            return True
        
        # Check if any known words are found
        all_words = set()
        for word in words:
            # Remove numbers and punctuation from word
            clean_word = ''.join(c for c in word.lower() if c.isalpha())
            all_words.add(clean_word)
        
        # Count recognized words
        recognized_count = len(all_words.intersection(common_words_en)) + \
                          len(all_words.intersection(common_words_id))
        
        # If very few recognized words, likely gibberish
        # For a 3-4 word phrase, we expect at least 1 recognized word
        if len(words) >= 2 and recognized_count == 0:
            return True
        
        # Check for repetitive character patterns (common in random input)
        alpha_only = ''.join(c for c in text_lower if c.isalpha())
        if len(alpha_only) >= 4:
            # Check for repeated character pairs
            pair_repeats = 0
            for i in range(len(alpha_only) - 3):
                if alpha_only[i:i+2] == alpha_only[i+2:i+4]:
                    pair_repeats += 1
            
            # Too many repeated pairs suggest gibberish
            if pair_repeats > len(alpha_only) / 10:
                return True
        
        # Check for words that are too short (mostly 1-2 chars)
        short_words = sum(1 for w in words if len(w) <= 2)
        if len(words) >= 3 and short_words / len(words) > 0.5:
            # If more than 50% are 1-2 char words, might be random
            # (unless they're common short words like 'a', 'I', 'an')
            recognized_short = sum(1 for w in all_words 
                                 if len(w) <= 2 and (w in common_words_en or w in common_words_id))
            if recognized_short < short_words:
                return True
        
        return False
    
    def _detect_language(self, text: str) -> Optional[str]:
        """
        Automatically detect the language of the input text.
        Uses multiple detection attempts and Indonesian word patterns for stability.
        
        Returns:
            Language code (e.g., 'en', 'id') or None if detection fails
        """
        try:
            # Remove numbers and special chars for better detection
            clean_text = ''.join(c for c in text if c.isalpha() or c.isspace())
            
            # Need at least some text for reliable detection
            if len(clean_text.strip()) < 3:
                return None
            
            # Check for common Indonesian words first (more reliable than langdetect)
            indonesian_indicators = {
                'saya', 'aku', 'anda', 'dia', 'kami', 'mereka', 'adalah', 'ada',
                'yang', 'untuk', 'dengan', 'dari', 'ke', 'pada', 'di', 'dan',
                'atau', 'tidak', 'ya', 'sholat', 'salat', 'tahajud', 'belajar', 
                'ingin', 'meningkatkan', 'kebiasaan', 'doa', 'ibadah', 'quran',
                'diri', 'hidup', 'bagaimana', 'mengapa', 'bisa', 'dapat', 'perlu',
                'harus', 'amalan', 'supaya', 'rezeki', 'lancar', 'berkah', 'agar',
                'semoga', 'insyallah', 'alhamdulillah', 'subhanallah', 'masya allah'
            }
            
            # Check for English words
            english_indicators = {
                'the', 'a', 'an', 'and', 'or', 'is', 'are', 'was', 'were', 'be',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
                'how', 'where', 'when', 'why', 'can', 'will', 'do', 'does', 'did',
                'have', 'has', 'should', 'would', 'could', 'want', 'need', 'help',
                'prayer', 'spiritual', 'improve', 'daily', 'habits', 'life'
            }
            
            # Normalize and check words
            words = set(word.lower() for word in clean_text.split())
            
            # Count matches
            indonesian_matches = len(words.intersection(indonesian_indicators))
            english_matches = len(words.intersection(english_indicators))
            
            # If we have clear Indonesian words, return Indonesian
            if indonesian_matches > 0:
                return 'id'
            
            # If we have clear English words, return English
            if english_matches > 0:
                return 'en'
            
            # If no clear indicators, try langdetect multiple times for consistency
            detection_results = []
            for _ in range(5):  # Try 5 times
                try:
                    result = detect(clean_text)
                    detection_results.append(result)
                except:
                    continue
            
            if not detection_results:
                return None
            
            # Count occurrences and pick most frequent
            from collections import Counter
            counter = Counter(detection_results)
            most_common = counter.most_common(1)[0][0]
            
            # Only return if it appears in majority of attempts (>= 3 out of 5)
            if counter[most_common] >= 3:
                return most_common
            
            return None
            
        except Exception:
            # Any error, fail gracefully
            return None
