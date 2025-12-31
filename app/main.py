"""
Hala AI Service
Multi-layer AI pipeline for Islamic spiritual journeys.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import HalaAIException
from app.api.v1.endpoints import health, journey
from app.api.deps import shutdown_services
from app.utils.logging import setup_logging, get_logger


# Setup logging
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Default LLM Provider: {settings.default_llm_provider}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    await shutdown_services()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="""
    Hala AI Service - Multi-layer AI pipeline for generating personalized 
    Islamic spiritual and productivity journeys.
    
    ## Features
    - 5-layer validation pipeline (sanitization, semantic, safety, RAG, inference)
    - Multiple LLM provider support (Gemini, OpenAI, Ollama)
    - RAG with ChromaDB for authentic Islamic sources
    - Bilingual support (Indonesian & English)
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HalaAIException)
async def hala_exception_handler(request: Request, exc: HalaAIException):
    """Handle custom Hala AI exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "code": exc.code,
            "message": {
                "id": exc.message_id,
                "en": exc.message_en,
            },
            "suggested_action": exc.suggested_action,
        },
    )


# Include routers
app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    journey.router,
    prefix=settings.api_v1_prefix,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }