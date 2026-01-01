"""
Sync API Endpoints
Provides REST API for running sync operations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.sync_service import SyncService
from app.services.chromadb_service import ChromaDBService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """Request model for sync operations."""
    force_full_sync: bool = False


class SyncResponse(BaseModel):
    """Response model for sync operations."""
    status: str
    knowledge_references_synced: int
    journey_templates_synced: int
    errors: int
    duration_seconds: float
    message: str


@router.post("/run", response_model=SyncResponse)
async def run_sync(request: SyncRequest):
    """
    Run data synchronization from PostgreSQL to ChromaDB.
    
    Args:
        request: Sync configuration
        - force_full_sync: If true, clears ChromaDB and syncs all data.
                         If false, only syncs new/updated items.
    
    Returns:
        Sync statistics and status
    """
    try:
        sync_service = SyncService()
        stats = await sync_service.sync_all(force_full_sync=request.force_full_sync)
        
        sync_type = "Full" if request.force_full_sync else "Incremental"
        message = f"{sync_type} sync completed successfully"
        
        if stats["errors"] > 0:
            message += f" with {stats['errors']} errors"
        
        return SyncResponse(
            status="success",
            knowledge_references_synced=stats["knowledge_references_synced"],
            journey_templates_synced=stats["journey_templates_synced"],
            errors=stats["errors"],
            duration_seconds=stats["duration_seconds"],
            message=message
        )
        
    except Exception as e:
        logger.error(f"Sync operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/knowledge-reference/{reference_id}")
async def sync_knowledge_reference(reference_id: str):
    """
    Sync a single knowledge reference.
    
    Args:
        reference_id: ID of the knowledge reference to sync
    
    Returns:
        Status of the sync operation
    """
    try:
        sync_service = SyncService()
        success = await sync_service.sync_knowledge_reference(reference_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Knowledge reference {reference_id} synced successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge reference {reference_id} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing knowledge reference: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/journey-template/{template_id}")
async def sync_journey_template(template_id: str):
    """
    Sync a single journey template.
    
    Args:
        template_id: ID of the journey template to sync
    
    Returns:
        Status of the sync operation
    """
    try:
        sync_service = SyncService()
        success = await sync_service.sync_journey_template(template_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Journey template {template_id} synced successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Journey template {template_id} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing journey template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/stats")
async def get_sync_stats():
    """
    Get ChromaDB collection statistics.
    
    Returns:
        Collection statistics (item counts, etc.)
    """
    try:
        chroma_service = ChromaDBService()
        await chroma_service.connect()
        
        stats = await chroma_service.get_collection_stats()
        
        await chroma_service.disconnect()
        
        return {
            "status": "success",
            "collections": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/health")
async def sync_health():
    """
    Health check for sync service.
    
    Returns:
        Health status and ChromaDB collection counts
    """
    try:
        chroma_service = ChromaDBService()
        await chroma_service.connect()
        
        stats = await chroma_service.get_collection_stats()
        
        await chroma_service.disconnect()
        
        return {
            "status": "healthy",
            "service": "sync",
            "collections": stats,
            "message": "Sync service is operational"
        }
        
    except Exception as e:
        logger.error(f"Sync service health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "sync",
            "error": str(e),
            "message": "Sync service is not operational"
        }
