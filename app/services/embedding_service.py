"""
Embedding Service
Handles text embedding using Sentence Transformers.
"""

from typing import Optional
import numpy as np
from app.core.config import settings


class EmbeddingService:
    """
    Service for generating text embeddings using Sentence Transformers.
    
    Uses all-MiniLM-L6-v2 by default (same model for validation and RAG).
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
    ):
        self._model_name = model_name or settings.embedding_model_name
        self._model = None
    
    async def initialize(self) -> None:
        """Initialize the embedding model (lazy loading)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        if self._model is None:
            await self.initialize()
        
        # SentenceTransformer.encode is CPU-bound, but fast enough
        # For true async, we'd need to run in executor
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding
    
    async def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Get embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of shape (n_texts, embedding_dim)
        """
        if self._model is None:
            await self.initialize()
        
        embeddings = self._model.encode(texts, convert_to_numpy=True)
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
