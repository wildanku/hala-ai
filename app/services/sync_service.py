"""
Sync Service
Synchronizes data between PostgreSQL and ChromaDB.
Handles KnowledgeReference and JourneyTemplate data.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.services.postgres_service import PostgresService
from app.services.chromadb_service import ChromaDBService

logger = logging.getLogger(__name__)


class SyncService:
    """Service to synchronize data between PostgreSQL and ChromaDB."""
    
    def __init__(self):
        self.postgres_service = PostgresService()
        self.chromadb_service = ChromaDBService()
        self.sync_stats = {
            "knowledge_references_synced": 0,
            "journey_templates_synced": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
        }
    
    async def sync_all(self, force_full_sync: bool = False) -> Dict[str, Any]:
        """
        Synchronize all data from PostgreSQL to ChromaDB.
        
        Args:
            force_full_sync: If True, clears ChromaDB and syncs everything.
                            If False, only syncs updated/new items.
        
        Returns:
            Dictionary with sync statistics
        """
        self.sync_stats["start_time"] = datetime.now()
        
        try:
            logger.info("Starting data synchronization...")
            
            # Connect to services
            await self.postgres_service.connect()
            await self.chromadb_service.connect()
            
            # Clear ChromaDB if force full sync
            if force_full_sync:
                logger.info("Clearing ChromaDB for full sync...")
                await self.chromadb_service.clear_all_collections()
            
            # Sync knowledge references
            logger.info("Syncing KnowledgeReference data...")
            await self._sync_knowledge_references()
            
            # Sync journey templates
            logger.info("Syncing JourneyTemplate data...")
            await self._sync_journey_templates()
            
            self.sync_stats["end_time"] = datetime.now()
            duration = (self.sync_stats["end_time"] - self.sync_stats["start_time"]).total_seconds()
            self.sync_stats["duration_seconds"] = duration
            
            logger.info(f"Synchronization completed in {duration:.2f}s")
            logger.info(f"Stats: {self.sync_stats}")
            
            return self.sync_stats
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}", exc_info=True)
            self.sync_stats["errors"] += 1
            raise
            
        finally:
            await self.postgres_service.disconnect()
            await self.chromadb_service.disconnect()
    
    async def _sync_knowledge_references(self) -> None:
        """Sync KnowledgeReference table to ChromaDB."""
        try:
            # Fetch all knowledge references
            references = await self.postgres_service.fetch_knowledge_references()
            logger.info(f"Found {len(references)} knowledge references")
            
            for reference in references:
                try:
                    # Prepare document for ChromaDB
                    document = self._prepare_knowledge_reference_document(reference)
                    
                    # Add to ChromaDB
                    await self.chromadb_service.add_knowledge_reference(document)
                    
                    self.sync_stats["knowledge_references_synced"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing knowledge reference {reference.get('id')}: {str(e)}")
                    self.sync_stats["errors"] += 1
                    continue
            
            logger.info(f"Successfully synced {self.sync_stats['knowledge_references_synced']} knowledge references")
            
        except Exception as e:
            logger.error(f"Error fetching knowledge references: {str(e)}")
            self.sync_stats["errors"] += 1
    
    async def _sync_journey_templates(self) -> None:
        """Sync JourneyTemplate table to ChromaDB."""
        try:
            # Fetch all journey templates
            templates = await self.postgres_service.fetch_journey_templates()
            logger.info(f"Found {len(templates)} journey templates")
            
            for template in templates:
                try:
                    # Prepare document for ChromaDB
                    document = self._prepare_journey_template_document(template)
                    
                    # Add to ChromaDB
                    await self.chromadb_service.add_journey_template(document)
                    
                    self.sync_stats["journey_templates_synced"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing journey template {template.get('id')}: {str(e)}")
                    self.sync_stats["errors"] += 1
                    continue
            
            logger.info(f"Successfully synced {self.sync_stats['journey_templates_synced']} journey templates")
            
        except Exception as e:
            logger.error(f"Error fetching journey templates: {str(e)}")
            self.sync_stats["errors"] += 1
    
    @staticmethod
    def _prepare_knowledge_reference_document(reference: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare KnowledgeReference document for ChromaDB embedding.
        
        Now handles single language content (plain text) instead of bilingual JSON.
        """
        # With new schema, title and content are plain strings
        title = reference.get("title", "")
        content = reference.get("content", "")
        language = reference.get("language", "id")
        
        # Build searchable text
        searchable_text_parts = []
        
        # Add title (now plain string)
        if title:
            searchable_text_parts.append(str(title))
        
        # Add content (now plain string)
        if content:
            searchable_text_parts.append(str(content))
        
        # Add tags
        tags = reference.get("tags", [])
        if tags:
            searchable_text_parts.append(" ".join(tags))
        
        # Add category
        category = reference.get("category", "")
        if category:
            searchable_text_parts.append(category)
        
        searchable_text = " ".join(searchable_text_parts)
        
        return {
            "id": reference.get("id"),
            "type": "knowledge_reference",
            "category": reference.get("category"),
            "source": reference.get("source"),
            "title": title,
            "content": content,
            "content_ar": reference.get("contentAr"),
            "tags": tags,
            "language": language,  # Single language field
            "status": reference.get("status"),
            "searchable_text": searchable_text,
            "created_at": reference.get("createdAt"),
            "updated_at": reference.get("updatedAt"),
        }
    
    @staticmethod
    def _prepare_journey_template_document(template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare JourneyTemplate document for ChromaDB embedding.
        
        Combines goal_keyword and tags for better searchability.
        """
        goal_keyword = template.get("goal_keyword", "")
        tags = template.get("tags", [])
        language = template.get("language", "id")  # Single language field
        full_json = template.get("full_json", {})
        
        # Build searchable text
        searchable_text_parts = [goal_keyword]
        searchable_text_parts.extend(tags)
        
        # Extract text from full_json if available
        if isinstance(full_json, dict):
            # Extract introduction if it's a string (new schema)
            intro = full_json.get("introduction", "")
            if isinstance(intro, str):
                searchable_text_parts.append(intro)
            
            # Extract goal
            goal = full_json.get("goal", "")
            if goal:
                searchable_text_parts.append(str(goal))
        
        searchable_text = " ".join(filter(None, searchable_text_parts))
        
        return {
            "id": template.get("id"),
            "type": "journey_template",
            "goal_keyword": goal_keyword,
            "tags": tags,
            "language": language,  # Single language field
            "is_active": template.get("is_active", False),
            "status": template.get("status"),
            "match_count": template.get("match_count", 0),
            "searchable_text": searchable_text,
            "full_json": full_json,
            "created_at": template.get("createdAt"),
            "updated_at": template.get("updatedAt"),
        }
    
    async def sync_knowledge_reference(self, reference_id: str) -> bool:
        """Sync a single knowledge reference."""
        try:
            await self.postgres_service.connect()
            await self.chromadb_service.connect()
            
            reference = await self.postgres_service.fetch_knowledge_reference(reference_id)
            if not reference:
                logger.warning(f"Knowledge reference {reference_id} not found")
                return False
            
            document = self._prepare_knowledge_reference_document(reference)
            await self.chromadb_service.add_knowledge_reference(document)
            
            logger.info(f"Successfully synced knowledge reference {reference_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing knowledge reference {reference_id}: {str(e)}")
            return False
            
        finally:
            await self.postgres_service.disconnect()
            await self.chromadb_service.disconnect()
    
    async def sync_journey_template(self, template_id: str) -> bool:
        """Sync a single journey template."""
        try:
            await self.postgres_service.connect()
            await self.chromadb_service.connect()
            
            template = await self.postgres_service.fetch_journey_template(template_id)
            if not template:
                logger.warning(f"Journey template {template_id} not found")
                return False
            
            document = self._prepare_journey_template_document(template)
            await self.chromadb_service.add_journey_template(document)
            
            logger.info(f"Successfully synced journey template {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing journey template {template_id}: {str(e)}")
            return False
            
        finally:
            await self.postgres_service.disconnect()
            await self.chromadb_service.disconnect()
