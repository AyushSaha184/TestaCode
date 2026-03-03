import os
import logging
from pathlib import Path

# ─── Load .env from project root ─────────────────────────────────────────────
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    PROJECT_NAME: str = "AI-Test-Gen"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/testgen")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8501")
    LOG_LEVEL: int = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)


settings = Settings()

# ─── Shared logger ────────────────────────────────────────────────────────────
# All backend modules should import `logger` from here or call get_logger(__name__)
from src.utils.logger import get_logger

logger = get_logger("ai_test_gen")
