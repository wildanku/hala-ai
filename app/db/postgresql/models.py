"""
PostgreSQL Models for Knowledge Base
These models store the source data that gets indexed into ChromaDB.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.postgresql.session import Base


class QuranVerse(Base):
    """Quran verses storage."""
    
    __tablename__ = "quran_verses"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    surah_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_arabic: Mapped[str] = mapped_column(Text, nullable=False)
    text_indonesian: Mapped[str] = mapped_column(Text, nullable=False)
    text_english: Mapped[str] = mapped_column(Text, nullable=False)
    themes: Mapped[Optional[str]] = mapped_column(String(500))  # Comma-separated themes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_quran_surah_ayah", "surah_number", "ayah_number"),
    )
    
    @property
    def reference(self) -> str:
        return f"QS. {self.surah_name} ({self.surah_number}): {self.ayah_number}"


class Hadith(Base):
    """Hadith collection storage."""
    
    __tablename__ = "hadith"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # Bukhari, Muslim, etc.
    book: Mapped[Optional[str]] = mapped_column(String(200))
    number: Mapped[Optional[str]] = mapped_column(String(50))
    narrator: Mapped[Optional[str]] = mapped_column(String(200))
    text_arabic: Mapped[Optional[str]] = mapped_column(Text)
    text_indonesian: Mapped[str] = mapped_column(Text, nullable=False)
    text_english: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[Optional[str]] = mapped_column(String(50))  # Sahih, Hasan, etc.
    themes: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_hadith_source", "source"),
    )
    
    @property
    def reference(self) -> str:
        ref = f"{self.source}"
        if self.number:
            ref += f" #{self.number}"
        return ref


class HalaStrategy(Base):
    """Proprietary Hala journaling strategies and prompts."""
    
    __tablename__ = "hala_strategies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # worship, mental_health, etc.
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # task, reflection, prompt
    content_id: Mapped[str] = mapped_column(Text, nullable=False)  # Indonesian content
    content_en: Mapped[str] = mapped_column(Text, nullable=False)  # English content
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20))  # easy, medium, hard
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_strategy_category", "category"),
        Index("ix_strategy_type", "strategy_type"),
    )
