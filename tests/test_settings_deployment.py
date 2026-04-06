from __future__ import annotations

from backend.core.config import Settings
import pytest


def test_cors_origins_include_vercel_url() -> None:
    settings = Settings(
        allowed_origins=["http://localhost:5173"],
        vercel_frontend_url="https://ai-test-gen.vercel.app",
        database_url="postgresql://example",
    )

    origins = settings.cors_origins()

    assert "http://localhost:5173" in origins
    assert "https://ai-test-gen.vercel.app" in origins


def test_production_requires_database_url() -> None:
    settings = Settings(app_env="production", database_url="")

    with pytest.raises(ValueError):
        settings.validate_production_configuration()
