from typing import Optional


class HalaAIException(Exception):
    """Base exception for Hala AI Service."""
    
    def __init__(
        self,
        code: str,
        message_id: str,
        message_en: str,
        suggested_action: Optional[str] = None,
    ):
        self.code = code
        self.message_id = message_id
        self.message_en = message_en
        self.suggested_action = suggested_action
        super().__init__(message_en)


class SanitizationError(HalaAIException):
    """Layer 1: Input sanitization failed."""
    
    def __init__(
        self,
        message_id: str = "Input tidak valid atau mengandung pola yang tidak diizinkan.",
        message_en: str = "Invalid input or contains disallowed patterns.",
        suggested_action: str = "Please provide a clear, genuine question about spiritual growth or productivity.",
    ):
        super().__init__(
            code="INJECTION_DETECTED",
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
        )


class SemanticScopeError(HalaAIException):
    """Layer 2: Input is out of platform scope."""
    
    def __init__(
        self,
        message_id: str = "Maaf, permintaanmu berada di luar jangkauan bimbingan Hala Journal.",
        message_en: str = "Sorry, your request is outside the scope of Hala Journal guidance.",
        suggested_action: str = "Try asking about spiritual habits, worship, mental health, or productivity.",
    ):
        super().__init__(
            code="OUT_OF_SCOPE",
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
        )


class SafetyViolationError(HalaAIException):
    """Layer 3: Safety or ethical violation detected."""
    
    def __init__(
        self,
        message_id: str = "Permintaan ini tidak dapat diproses karena melanggar pedoman keamanan.",
        message_en: str = "This request cannot be processed due to safety guideline violations.",
        suggested_action: str = "If you're struggling, please reach out to a mental health professional or call a helpline.",
    ):
        super().__init__(
            code="SAFETY_VIOLATION",
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
        )


class RAGRetrievalError(HalaAIException):
    """Layer 4: Failed to retrieve context from vector database."""
    
    def __init__(
        self,
        message_id: str = "Gagal mengambil konteks yang relevan dari basis pengetahuan.",
        message_en: str = "Failed to retrieve relevant context from knowledge base.",
        suggested_action: str = "Please try again or rephrase your question.",
    ):
        super().__init__(
            code="RAG_FAILURE",
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
        )


class LLMInferenceError(HalaAIException):
    """Layer 5: LLM inference failed."""
    
    def __init__(
        self,
        message_id: str = "Gagal menghasilkan respons dari model AI.",
        message_en: str = "Failed to generate response from AI model.",
        suggested_action: str = "Please try again in a few moments.",
    ):
        super().__init__(
            code="LLM_FAILURE",
            message_id=message_id,
            message_en=message_en,
            suggested_action=suggested_action,
        )


class ProviderNotFoundError(HalaAIException):
    """LLM Provider not found or not configured."""
    
    def __init__(self, provider_name: str):
        super().__init__(
            code="PROVIDER_NOT_FOUND",
            message_id=f"Provider '{provider_name}' tidak ditemukan atau tidak dikonfigurasi.",
            message_en=f"Provider '{provider_name}' not found or not configured.",
            suggested_action="Check your configuration and ensure the provider is properly set up.",
        )
