"""
ChromaDB Service
Handles connections and operations with ChromaDB vector database.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import chromadb
import logging
import json

logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Any:
    """Convert non-JSON-serializable values to strings."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize all values in a document for JSON storage."""
    return {k: _serialize_value(v) for k, v in doc.items()}


class ChromaDBService:
    """Service for ChromaDB vector database operations."""
    
    def __init__(self, persist_directory: str = "./chromadb_data"):
        self.persist_directory = persist_directory
        self.client: Optional[chromadb.PersistentClient] = None
        self.knowledge_ref_collection = None
        self.journey_template_collection = None
    
    async def connect(self) -> None:
        """Initialize ChromaDB client and collections."""
        if self.client is not None:
            return
        
        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Get or create collections
            self.knowledge_ref_collection = self.client.get_or_create_collection(
                name="knowledge_references",
                metadata={"description": "Knowledge references (verses, hadith, strategies, doa)"}
            )
            
            self.journey_template_collection = self.client.get_or_create_collection(
                name="journey_templates",
                metadata={"description": "Journey templates for different user goals"}
            )
            
            logger.info("Connected to ChromaDB")
            logger.info(f"Knowledge references collection: {self.knowledge_ref_collection.count()} items")
            logger.info(f"Journey templates collection: {self.journey_template_collection.count()} items")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Close ChromaDB connection."""
        # ChromaDB is file-based, no explicit disconnect needed
        self.client = None
        self.knowledge_ref_collection = None
        self.journey_template_collection = None
        logger.info("Disconnected from ChromaDB")
    
    async def clear_all_collections(self) -> None:
        """Delete and recreate all collections (for full sync)."""
        if not self.client:
            raise RuntimeError("ChromaDB connection not initialized")
        
        try:
            logger.info("Clearing all ChromaDB collections...")
            
            # Delete collections if they exist
            try:
                self.client.delete_collection(name="knowledge_references")
            except:
                pass
            
            try:
                self.client.delete_collection(name="journey_templates")
            except:
                pass
            
            # Recreate collections
            self.knowledge_ref_collection = self.client.get_or_create_collection(
                name="knowledge_references",
                metadata={"description": "Knowledge references (verses, hadith, strategies, doa)"}
            )
            
            self.journey_template_collection = self.client.get_or_create_collection(
                name="journey_templates",
                metadata={"description": "Journey templates for different user goals"}
            )
            
            logger.info("All collections cleared and recreated")
            
        except Exception as e:
            logger.error(f"Error clearing collections: {str(e)}")
            raise
    
    async def add_knowledge_reference(self, document: Dict[str, Any]) -> None:
        """Add or update a knowledge reference in ChromaDB."""
        if not self.knowledge_ref_collection:
            raise RuntimeError("ChromaDB connection not initialized")
        
        try:
            # Prepare data for ChromaDB
            doc_id = document["id"]
            searchable_text = document["searchable_text"]
            
            # Metadata for filtering
            metadata = {
                "type": "knowledge_reference",
                "category": document.get("category", ""),
                "source": document.get("source", ""),
                "status": document.get("status", ""),
                "languages": ",".join(document.get("languages", ["id", "en"])),
            }
            
            # Add tags as metadata for filtering
            if document.get("tags"):
                metadata["tags"] = ",".join(document["tags"])
            
            # Store full document as metadata (serialized JSON with datetime handling)
            serializable_doc = _serialize_document({
                k: v for k, v in document.items() 
                if k not in ["searchable_text"]
            })
            metadata["full_document"] = json.dumps(serializable_doc)
            
            # Upsert to ChromaDB
            self.knowledge_ref_collection.upsert(
                ids=[doc_id],
                documents=[searchable_text],
                metadatas=[metadata]
            )
            
            logger.debug(f"Added knowledge reference {doc_id} to ChromaDB")
            
        except Exception as e:
            logger.error(f"Error adding knowledge reference {document.get('id')}: {str(e)}")
            raise
    
    async def add_journey_template(self, document: Dict[str, Any]) -> None:
        """Add or update a journey template in ChromaDB."""
        if not self.journey_template_collection:
            raise RuntimeError("ChromaDB connection not initialized")
        
        try:
            # Prepare data for ChromaDB
            doc_id = document["id"]
            searchable_text = document["searchable_text"]
            
            # Metadata for filtering
            metadata = {
                "type": "journey_template",
                "goal_keyword": document.get("goal_keyword", ""),
                "is_active": str(document.get("is_active", False)),
                "status": document.get("status", ""),
                "languages": ",".join(document.get("languages", ["id", "en"])),
                "match_count": str(document.get("match_count", 0)),
            }
            
            # Add tags as metadata for filtering
            if document.get("tags"):
                metadata["tags"] = ",".join(document["tags"])
            
            # Store full document as metadata (serialized JSON with datetime handling)
            serializable_doc = _serialize_document({
                k: v for k, v in document.items() 
                if k not in ["searchable_text"]
            })
            metadata["full_document"] = json.dumps(serializable_doc)
            
            # Upsert to ChromaDB
            self.journey_template_collection.upsert(
                ids=[doc_id],
                documents=[searchable_text],
                metadatas=[metadata]
            )
            
            logger.debug(f"Added journey template {doc_id} to ChromaDB")
            
        except Exception as e:
            logger.error(f"Error adding journey template {document.get('id')}: {str(e)}")
            raise
    
    async def search_knowledge_references(
        self, 
        query: str, 
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge references by semantic similarity."""
        if not self.knowledge_ref_collection:
            raise RuntimeError("ChromaDB connection not initialized")
        
        try:
            # Build where filter if category is specified
            where_filter = None
            if category:
                where_filter = {"category": category}
            
            # Search
            results = self.knowledge_ref_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )
            
            # Format results
            formatted_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    result = {
                        "id": doc_id,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }
                    
                    # Parse full document if available
                    if "full_document" in result["metadata"]:
                        try:
                            result["document"] = json.loads(result["metadata"]["full_document"])
                        except:
                            pass
                    
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge references: {str(e)}")
            raise
    
    async def search_journey_templates(
        self, 
        query: str, 
        limit: int = 5,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search journey templates by semantic similarity."""
        if not self.journey_template_collection:
            raise RuntimeError("ChromaDB connection not initialized")
        
        try:
            # Build where filter if active_only
            where_filter = None
            if active_only:
                where_filter = {"is_active": "True"}
            
            # Search
            results = self.journey_template_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )
            
            # Format results
            formatted_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    result = {
                        "id": doc_id,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }
                    
                    # Parse full document if available
                    if "full_document" in result["metadata"]:
                        try:
                            result["document"] = json.loads(result["metadata"]["full_document"])
                        except:
                            pass
                    
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching journey templates: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about ChromaDB collections."""
        if not self.client:
            raise RuntimeError("ChromaDB connection not initialized")
        
        return {
            "knowledge_references": {
                "count": self.knowledge_ref_collection.count() if self.knowledge_ref_collection else 0,
            },
            "journey_templates": {
                "count": self.journey_template_collection.count() if self.journey_template_collection else 0,
            }
        }
