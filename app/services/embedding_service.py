"""
Embedding Service
Handles text embedding using Sentence Transformers.
"""

from typing import Optional
import numpy as np
from app.core.config import settings
import asyncio
import threading


class EmbeddingService:
    """
    Singleton service for generating text embeddings using Sentence Transformers.
    
    Uses all-MiniLM-L6-v2 by default (same model for validation and RAG).
    Implements singleton pattern for model reuse across requests.
    """
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        model_name: Optional[str] = None,
    ):
        if not hasattr(self, '_model_name'):
            self._model_name = model_name or settings.embedding_model_name
    
    async def initialize(self) -> None:
        """Initialize the embedding model (lazy loading with singleton pattern)."""
        if EmbeddingService._initialized:
            return
            
        if EmbeddingService._model is None:
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)
            EmbeddingService._initialized = True
    
    def _load_model(self):
        """Load the model synchronously (called from executor)."""
        if EmbeddingService._model is None:
            from sentence_transformers import SentenceTransformer
            EmbeddingService._model = SentenceTransformer(self._model_name)
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        if not EmbeddingService._initialized:
            await self.initialize()
        
        # Run embedding in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: EmbeddingService._model.encode(text, convert_to_numpy=True)
        )
        return embedding
    
    async def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Get embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of shape (n_texts, embedding_dim)
        """
        if not EmbeddingService._initialized:
            await self.initialize()
        
        # Run batch embedding in executor for better performance
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: EmbeddingService._model.encode(texts, convert_to_numpy=True)
        )
        return embeddings
    
    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        # MiniLM-L6-v2 outputs 384-dimensional vectors
        dimension_map = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
        }
        return dimension_map.get(self._model_name, 384)
