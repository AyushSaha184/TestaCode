import os
import logging
from logging.handlers import RotatingFileHandler
import sys

class Settings:
    PROJECT_NAME: str = "AI-Test-Gen"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./database/testgen.db")
    LOG_LEVEL: int = logging.INFO

settings = Settings()

def setup_logging():
    logger = logging.getLogger("ai_test_gen")
    logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(settings.LOG_LEVEL)
    ch.setFormatter(formatter)
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Rotating File Handler (10MB max, keep 5 backups)
    fh = RotatingFileHandler(os.path.join("logs", "app.log"), maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(settings.LOG_LEVEL)
    fh.setFormatter(formatter)

    # Prevent duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)
        
    return logger

logger = setup_logging()
