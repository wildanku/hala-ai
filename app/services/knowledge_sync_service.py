"""
Knowledge Base Sync Service
Handles syncing data from PostgreSQL to ChromaDB.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgresql.models import QuranVerse, Hadith, HalaStrategy
from app.db.vector.chroma_store import ChromaVectorStore
from app.services.embedding_service import EmbeddingService


class KnowledgeBaseSyncService:
    """
    Service for syncing knowledge base from PostgreSQL to ChromaDB.
    
    This ensures your RAG vector store stays up-to-date with source data.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        vector_store: ChromaVectorStore,
        embedding_service: EmbeddingService,
    ):
        self._db = db_session
        self._vector_store = vector_store
        self._embedding_service = embedding_service
    
    async def sync_quran_verses(self, batch_size: int = 100) -> int:
        """Sync Quran verses to ChromaDB."""
        result = await self._db.execute(select(QuranVerse))
        verses = result.scalars().all()
        
        documents = []
        for verse in verses:
            # Combine texts for better semantic matching
            combined_text = f"{verse.text_indonesian} {verse.text_english}"
            
            documents.append({
                "id": f"quran_{verse.id}",
                "text": combined_text,
                "reference": verse.reference,
                "surah_name": verse.surah_name,
                "surah_number": verse.surah_number,
                "ayah_number": verse.ayah_number,
                "text_arabic": verse.text_arabic,
                "text_indonesian": verse.text_indonesian,
                "text_english": verse.text_english,
                "themes": verse.themes,
            })
        
        if documents:
            await self._vector_store.add_documents(
                collection_name=ChromaVectorStore.QURAN_COLLECTION,
                documents=documents,
            )
        
        return len(documents)
    
    async def sync_hadith(self, batch_size: int = 100) -> int:
        """Sync Hadith to ChromaDB."""
        result = await self._db.execute(select(Hadith))
        hadith_list = result.scalars().all()
        
        documents = []
        for hadith in hadith_list:
            combined_text = f"{hadith.text_indonesian} {hadith.text_english}"
            
            documents.append({
                "id": f"hadith_{hadith.id}",
                "text": combined_text,
                "source": hadith.source,
                "reference": hadith.reference,
                "narrator": hadith.narrator,
                "text_indonesian": hadith.text_indonesian,
                "text_english": hadith.text_english,
                "grade": hadith.grade,
                "themes": hadith.themes,
            })
        
        if documents:
            await self._vector_store.add_documents(
                collection_name=ChromaVectorStore.HADITH_COLLECTION,
                documents=documents,
            )
        
        return len(documents)
    
    async def sync_strategies(self, batch_size: int = 100) -> int:
        """Sync Hala strategies to ChromaDB."""
        result = await self._db.execute(
            select(HalaStrategy).where(HalaStrategy.is_active == True)
        )
        strategies = result.scalars().all()
        
        documents = []
        for strategy in strategies:
            combined_text = f"{strategy.title} {strategy.description} {strategy.content_id} {strategy.content_en}"
            
            documents.append({
                "id": f"strategy_{strategy.id}",
                "text": combined_text,
                "title": strategy.title,
                "description": strategy.description,
                "category": strategy.category,
                "strategy_type": strategy.strategy_type,
                "content_id": strategy.content_id,
                "content_en": strategy.content_en,
            })
        
        if documents:
            await self._vector_store.add_documents(
                collection_name=ChromaVectorStore.STRATEGIES_COLLECTION,
                documents=documents,
            )
        
        return len(documents)
    
    async def sync_all(self) -> dict[str, int]:
        """Sync all knowledge base collections."""
        results = {
            "quran_verses": await self.sync_quran_verses(),
            "hadith": await self.sync_hadith(),
            "strategies": await self.sync_strategies(),
        }
        return results
