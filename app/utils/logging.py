"""
Logging Configuration
Structured logging for the application.
"""

import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Custom log format string
        
    Returns:
        Configured root logger
    """
    level = log_level or ("DEBUG" if settings.debug else "INFO")
    
    format_string = log_format or (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    
    return logging.getLogger("hala_ai")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"hala_ai.{name}")
