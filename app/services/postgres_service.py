"""
PostgreSQL Service
Handles connections and queries to PostgreSQL database.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
import asyncpg
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class PostgresService:
    """Service for PostgreSQL database operations."""
    
    def __init__(self, connection_string: Optional[str] = None):
        # Use connection string from settings if not provided
        # asyncpg requires "postgresql://" scheme, but sqlalchemy uses "postgresql+asyncpg://"
        self.connection_string = connection_string or settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Create connection pool to PostgreSQL."""
        if self.pool is not None:
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL")
    
    async def fetch_knowledge_references(
        self, 
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all knowledge references from database.
        
        Args:
            language: Optional language filter ('id' or 'en')
        """
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        # Base query for new schema (single language field, plain text content)
        query = """
            SELECT 
                id,
                category,
                source,
                title,
                content,
                "contentAr",
                tags,
                language,
                status,
                "createdAt",
                "updatedAt"
            FROM "KnowledgeReference"
            WHERE status != 'REJECTED'
        """
        
        params = []
        if language:
            query += " AND language = $1"
            params.append(language)
        
        query += ' ORDER BY "updatedAt" DESC'
        
        async with self.pool.acquire() as connection:
            if params:
                rows = await connection.fetch(query, *params)
            else:
                rows = await connection.fetch(query)
            
            # Convert rows to dictionaries (title and content are now plain text)
            results = []
            for row in rows:
                result = dict(row)
                results.append(result)
            
            return results
    
    async def fetch_knowledge_reference(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single knowledge reference by ID."""
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        query = """
            SELECT 
                id,
                category,
                source,
                title,
                content,
                "contentAr",
                tags,
                language,
                status,
                "createdAt",
                "updatedAt"
            FROM "KnowledgeReference"
            WHERE id = $1
        """
        
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, reference_id)
            
            if not row:
                return None
            
            # Title and content are now plain text, no JSON parsing needed
            result = dict(row)
            return result
    
    async def fetch_journey_templates(
        self, 
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all journey templates from database.
        
        Args:
            language: Optional language filter ('id' or 'en')
        """
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        query = """
            SELECT 
                id,
                goal_keyword,
                tags,
                language,
                full_json,
                status::text,
                is_active,
                match_count,
                "createdAt",
                "updatedAt"
            FROM "JourneyTemplate"
            WHERE status::text != 'ARCHIVED'
        """
        
        params = []
        if language:
            query += " AND language = $1"
            params.append(language)
        
        query += ' ORDER BY "updatedAt" DESC'
        
        async with self.pool.acquire() as connection:
            if params:
                rows = await connection.fetch(query, *params)
            else:
                rows = await connection.fetch(query)
            
            # Convert rows to dictionaries
            results = []
            for row in rows:
                result = dict(row)
                # Ensure JSON fields are properly parsed
                if isinstance(result.get("full_json"), str):
                    result["full_json"] = json.loads(result["full_json"])
                results.append(result)
            
            return results
    
    async def fetch_journey_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single journey template by ID."""
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        query = """
            SELECT 
                id,
                goal_keyword,
                tags,
                language,
                full_json,
                status::text,
                is_active,
                match_count,
                "createdAt",
                "updatedAt"
            FROM "JourneyTemplate"
            WHERE id = $1
        """
        
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, template_id)
            
            if not row:
                return None
            
            result = dict(row)
            # Parse JSON fields
            if isinstance(result.get("full_json"), str):
                result["full_json"] = json.loads(result["full_json"])
            
            return result
    
    async def get_knowledge_references_updated_since(self, timestamp: str) -> List[Dict[str, Any]]:
        """Fetch knowledge references updated since a specific timestamp."""
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        query = """
            SELECT 
                id,
                category,
                source,
                title,
                content,
                "contentAr",
                tags,
                language,
                status,
                "createdAt",
                "updatedAt"
            FROM "KnowledgeReference"
            WHERE "updatedAt" > $1 AND status != 'REJECTED'
            ORDER BY "updatedAt" DESC
        """
        
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, timestamp)
            
            # Title and content are now plain text
            results = []
            for row in rows:
                result = dict(row)
                results.append(result)
            
            return results
    
    async def get_journey_templates_updated_since(self, timestamp: str) -> List[Dict[str, Any]]:
        """Fetch journey templates updated since a specific timestamp."""
        if not self.pool:
            raise RuntimeError("Database connection not initialized")
        
        query = """
            SELECT 
                id,
                goal_keyword,
                tags,
                language,
                full_json,
                status::text,
                is_active,
                match_count,
                "createdAt",
                "updatedAt"
            FROM "JourneyTemplate"
            WHERE "updatedAt" > $1 AND status::text != 'ARCHIVED'
            ORDER BY "updatedAt" DESC
        """
        
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, timestamp)
            
            results = []
            for row in rows:
                result = dict(row)
                if isinstance(result.get("full_json"), str):
                    result["full_json"] = json.loads(result["full_json"])
                results.append(result)
            
            return results
