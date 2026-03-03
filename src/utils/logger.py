"""
src/utils/logger.py
-------------------
Structured logging for AI Test Generator using structlog.

In development (LOG_FORMAT=dev): pretty, colored console output.
In production (LOG_FORMAT=json): newline-delimited JSON, also mirrored to
    logs/app.log via the stdlib rotating file handler.

Usage:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("job_created", job_id=42, language="python")
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"
_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per file
_BACKUP_COUNT = 5

_configured = False


def _configure_structlog() -> None:
    """One-time global structlog configuration — safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_format = os.getenv("LOG_FORMAT", "dev").lower()  # "dev" or "json"

    # ── Stdlib root logger setup ─────────────────────────────────────────────
    # structlog delegates to stdlib for the actual I/O — configure it here.
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    fmt = logging.Formatter("%(message)s")   # structlog already pre-formats

    # Console
    if not any(isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
               for h in root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(fmt)
        root_logger.addHandler(console_handler)

    # Rotating file
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        file_handler = RotatingFileHandler(
            str(_LOG_FILE),
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(fmt)
        root_logger.addHandler(file_handler)

    # ── Shared processors (always applied) ───────────────────────────────────
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # Machine-readable JSON (for deployed environments)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-friendly, colorized dev output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Attach the structlog formatter to the file handler so JSON lands in file too
    structlog_formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    for handler in root_logger.handlers:
        handler.setFormatter(structlog_formatter)


def get_logger(name: str = "ai_test_gen") -> structlog.stdlib.BoundLogger:
    """
    Returns a bound structlog logger.
    The first call triggers a one-time global configuration.

    Usage:
        logger = get_logger(__name__)
        logger.info("request_started", method="POST", path="/generate")
        logger.error("db_error", exc_info=True, job_id=job.id)
    """
    _configure_structlog()
    return structlog.get_logger(name)
