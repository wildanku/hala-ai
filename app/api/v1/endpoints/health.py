"""
Health Check Endpoints
"""

from fastapi import APIRouter, Depends
from app.api.deps import get_embedding_service, get_vector_store
from app.providers.factory import LLMProviderFactory
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check including all dependencies.
    """
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {},
    }
    
    # Check embedding service
    try:
        embedding_service = await get_embedding_service()
        health_status["components"]["embedding_service"] = {
            "status": "healthy",
            "model": settings.embedding_model_name,
        }
    except Exception as e:
        health_status["components"]["embedding_service"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Check vector store
    try:
        vector_store = await get_vector_store()
        health_status["components"]["vector_store"] = {
            "status": "healthy",
            "type": "chromadb",
        }
    except Exception as e:
        health_status["components"]["vector_store"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"
    
    # Check LLM providers
    available_providers = LLMProviderFactory.get_available_providers()
    healthy_providers = await LLMProviderFactory.get_healthy_providers()
    
    health_status["components"]["llm_providers"] = {
        "available": available_providers,
        "healthy": healthy_providers,
        "default": settings.default_llm_provider,
    }
    
    if settings.default_llm_provider not in healthy_providers:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/providers")
async def list_providers():
    """List available LLM providers and their status."""
    providers = {}
    
    for provider_name in LLMProviderFactory.get_available_providers():
        is_healthy = await LLMProviderFactory.check_provider_health(provider_name)
        providers[provider_name] = {
            "available": is_healthy,
            "is_default": provider_name == settings.default_llm_provider,
        }
    
    return {
        "providers": providers,
        "default_provider": settings.default_llm_provider,
    }
