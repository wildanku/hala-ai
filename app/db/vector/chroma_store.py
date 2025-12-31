"""
ChromaDB Vector Store
Handles semantic search for RAG (Retrieval-Augmented Generation).
"""

from typing import Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings


class ChromaVectorStore:
    """
    ChromaDB vector store for semantic search.
    
    Manages collections for:
    - Quran verses
    - Hadith
    - Hala strategies
    """
    
    # Collection names
    QURAN_COLLECTION = "quran_verses"
    HADITH_COLLECTION = "hadith"
    STRATEGIES_COLLECTION = "hala_strategies"
    
    def __init__(
        self,
        embedding_service=None,
        persist_directory: Optional[str] = None,
    ):
        self._embedding_service = embedding_service
        self._persist_directory = persist_directory or settings.chroma_persist_directory
        self._client: Optional[chromadb.Client] = None
        self._collections: dict[str, chromadb.Collection] = {}
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        # Create persistent client
        self._client = chromadb.PersistentClient(
            path=self._persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        
        # Initialize collections
        for collection_name in [
            self.QURAN_COLLECTION,
            self.HADITH_COLLECTION,
            self.STRATEGIES_COLLECTION,
        ]:
            self._collections[collection_name] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
    
    async def add_documents(
        self,
        collection_name: str,
        documents: list[dict[str, Any]],
        id_field: str = "id",
        text_field: str = "text",
    ) -> int:
        """
        Add documents to a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document dicts with id, text, and metadata
            id_field: Field name for document ID
            text_field: Field name for text content
            
        Returns:
            Number of documents added
        """
        if collection_name not in self._collections:
            raise ValueError(f"Collection '{collection_name}' not found")
        
        collection = self._collections[collection_name]
        
        ids = []
        texts = []
        metadatas = []
        embeddings = []
        
        for doc in documents:
            doc_id = str(doc.get(id_field))
            text = doc.get(text_field, "")
            
            # Get embedding for the text
            if self._embedding_service:
                embedding = await self._embedding_service.get_embedding(text)
                embeddings.append(embedding.tolist())
            
            # Build metadata (exclude id and text fields)
            metadata = {k: v for k, v in doc.items() if k not in [id_field, text_field] and v is not None}
            
            ids.append(doc_id)
            texts.append(text)
            metadatas.append(metadata)
        
        # Add to collection
        if embeddings:
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        else:
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
            )
        
        return len(documents)
    
    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search in a collection.
        
        Args:
            collection_name: Name of the collection to search
            query_embedding: Query vector embedding
            top_k: Number of results to return
            where: Optional filter conditions
            
        Returns:
            List of matching documents with metadata
        """
        if collection_name not in self._collections:
            # Return empty list for non-existent collections (graceful degradation)
            return []
        
        collection = self._collections[collection_name]
        
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        
        if where:
            query_params["where"] = where
        
        results = collection.query(**query_params)
        
        # Format results
        documents = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = {
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
                if results["metadatas"] and results["metadatas"][0]:
                    doc.update(results["metadatas"][0][i])
                documents.append(doc)
        
        return documents
    
    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Search by text (generates embedding internally).
        
        Convenience method when you have text instead of embedding.
        """
        if self._embedding_service is None:
            raise RuntimeError("Embedding service not configured")
        
        embedding = await self._embedding_service.get_embedding(query_text)
        return await self.search(
            collection_name=collection_name,
            query_embedding=embedding.tolist(),
            top_k=top_k,
            where=where,
        )
    
    async def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        if self._client:
            self._client.delete_collection(collection_name)
            self._collections.pop(collection_name, None)
    
    async def get_collection_count(self, collection_name: str) -> int:
        """Get number of documents in a collection."""
        if collection_name not in self._collections:
            return 0
        return self._collections[collection_name].count()
    
    async def reset(self) -> None:
        """Reset all collections (use with caution)."""
        if self._client:
            self._client.reset()
            self._collections.clear()
