from __future__ import annotations

from backend.core.config import Settings


def _make_settings(**overrides) -> Settings:
    """Create Settings with explicit overrides, bypassing env/dotenv."""
    defaults = dict(
        app_name="test", app_env="development", log_level="INFO",
        log_file="logs/test.log", log_to_file=False,
        allowed_origins=["http://localhost"], database_url="",
        render_external_url="", vercel_frontend_url="",
        max_upload_kb=50, request_timeout_seconds=40,
        parser_cache_ttl_seconds=600, intent_cache_ttl_seconds=600,
        idempotency_ttl_seconds=3600,
        llm_enabled=False, llm_api_key="",
        openrouter_api_key="", google_api_key="", llm_base_url="",
        cerebras_api_key="",
        llm_fast_model="gpt-4o-mini", llm_strong_model="gpt-4.1",
        llm_timeout_seconds=25, llm_max_retries=3,
        llm_enable_self_eval=False, llm_gen_timeout_seconds=20,
        llm_gen_max_retries=1,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_self_eval_disabled_by_default():
    """LLM_ENABLE_SELF_EVAL defaults to false."""
    settings = _make_settings()
    assert settings.llm_enable_self_eval is False


def test_self_eval_can_be_enabled():
    settings = _make_settings(llm_enable_self_eval=True)
    assert settings.llm_enable_self_eval is True


def test_gen_timeout_defaults():
    settings = _make_settings()
    assert settings.llm_gen_timeout_seconds == 20
    assert settings.llm_gen_max_retries == 1


def test_gen_timeout_can_be_overridden():
    settings = _make_settings(llm_gen_timeout_seconds=15, llm_gen_max_retries=2)
    assert settings.llm_gen_timeout_seconds == 15
    assert settings.llm_gen_max_retries == 2
