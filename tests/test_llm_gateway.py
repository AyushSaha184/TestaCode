from __future__ import annotations

from backend.agents.llm_gateway import LLMGateway
from backend.core.config import Settings


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _AlwaysFailModel:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        raise self.error


class _SuccessModel:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        return _Message(self.text)


def _make_settings(**overrides) -> Settings:
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
        redis_key_prefix="test", llm_enabled=True, llm_api_key="",
        openrouter_api_key="", google_api_key="", llm_base_url="",
        llm_fast_model="gemini-3-flash-preview", llm_strong_model="minimax/minimax-m2.5:free",
        llm_timeout_seconds=1, llm_max_retries=3,
        llm_enable_self_eval=False, llm_gen_timeout_seconds=20,
        llm_gen_max_retries=1, auto_commit_default=False,
        git_author_name="bot", git_author_email="bot@test.com",
        enable_git_push=False, repository_root=".", generated_tests_dir="generated_tests",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_fast_tier_non_retryable_falls_back_to_strong() -> None:
    settings = _make_settings(llm_max_retries=3)
    gateway = LLMGateway(settings)
    fast_error = RuntimeError("403 PERMISSION_DENIED. Your API key was reported as leaked")
    fast = _AlwaysFailModel(fast_error)
    strong = _SuccessModel('{"quality_score": 8, "uncovered_areas": []}')

    gateway._fast = fast
    gateway._strong = strong

    result = gateway.invoke_text(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert result == '{"quality_score": 8, "uncovered_areas": []}'
    assert fast.calls == 1
    assert strong.calls == 1


def test_fast_tier_non_retryable_falls_back_to_local_when_no_strong() -> None:
    settings = _make_settings(llm_max_retries=3)
    gateway = LLMGateway(settings)
    fast_error = RuntimeError("403 PERMISSION_DENIED. Your API key was reported as leaked")
    fast = _AlwaysFailModel(fast_error)

    gateway._fast = fast
    gateway._strong = None

    payload = gateway.invoke_json(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert payload["target_framework"] == "unspecified"
    assert payload["test_type"] == "mixed"
    assert fast.calls == 1


def test_strong_tier_falls_back_to_fast_when_strong_unavailable() -> None:
    settings = _make_settings(llm_max_retries=1)
    gateway = LLMGateway(settings)
    fast = _SuccessModel("describe('discount', () => { it('works', () => {}); });")

    gateway._fast = fast
    gateway._strong = None

    result = gateway.invoke_text(
        "You are a senior test generator",
        "Generate Jest tests",
        tier="strong",
    )

    assert "describe(" in result
    assert fast.calls == 1
