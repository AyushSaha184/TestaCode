"""
backend/core/logger.py
-----------------------
Convenience re-export so backend modules can import the shared logger without
reaching into src/ directly.

Usage inside backend:
    from backend.core.logger import get_logger
    logger = get_logger(__name__)
"""

from src.utils.logger import get_logger

__all__ = ["get_logger"]
