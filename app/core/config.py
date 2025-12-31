from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # App Settings
    app_name: str = "Hala AI Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    # API Settings
    api_v1_prefix: str = "/api/v1"
    
    # PostgreSQL Settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "hala_ai"
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # ChromaDB Settings
    chroma_persist_directory: str = "./data/chromadb"
    chroma_collection_name: str = "hala_knowledge_base"
    
    # Embedding Model Settings
    embedding_model_name: str = "all-MiniLM-L6-v2"
    
    # LLM Provider Settings
    default_llm_provider: Literal["gemini", "openai", "ollama"] = "gemini"
    
    # Gemini Settings
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-1.5-flash"
    
    # OpenAI Settings (Future)
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"
    
    # Ollama Settings (Future - Local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "llama3.2"
    
    # Pipeline Layer Settings
    # Layer 1: Sanitization
    min_input_length: int = 10
    max_input_length: int = 500
    
    # Layer 2: Semantic Validation
    semantic_similarity_threshold: float = 0.45
    
    # Layer 4: RAG
    rag_top_k_results: int = 5


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
