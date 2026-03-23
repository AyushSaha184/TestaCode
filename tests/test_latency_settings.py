from __future__ import annotations

from backend.core.config import Settings


def _make_settings(**overrides) -> Settings:
    """Create Settings with explicit overrides, bypassing env/dotenv."""
    defaults = dict(
        app_name="test", app_env="development", log_level="INFO",
        log_file="logs/test.log", log_to_file=False,
        allowed_origins=["http://localhost"], database_url="",
        supabase_url="", supabase_anon_key="", supabase_service_role_key="",
        supabase_storage_bucket="code-files", supabase_storage_public=False,
        supabase_signed_url_ttl_seconds=3600, render_external_url="",
        vercel_frontend_url="", max_upload_kb=50, request_timeout_seconds=40,
        parser_cache_ttl_seconds=600, intent_cache_ttl_seconds=600,
        idempotency_ttl_seconds=3600, use_redis_cache=False,
        redis_url="", redis_host="", redis_port=6379,
        redis_username="", redis_password="", redis_ssl=False,
        redis_key_prefix="test", llm_enabled=False, llm_api_key="",
        openrouter_api_key="", google_api_key="", llm_base_url="",
        llm_fast_model="gpt-4o-mini", llm_strong_model="gpt-4.1",
        llm_timeout_seconds=25, llm_max_retries=3,
        llm_enable_self_eval=False, llm_gen_timeout_seconds=20,
        llm_gen_max_retries=1, auto_commit_default=False,
        git_author_name="bot", git_author_email="bot@test.com",
        enable_git_push=False, repository_root=".", generated_tests_dir="generated_tests",
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
