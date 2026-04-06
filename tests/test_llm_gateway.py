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
        render_external_url="",
        vercel_frontend_url="", max_upload_kb=50, request_timeout_seconds=40,
        parser_cache_ttl_seconds=600, intent_cache_ttl_seconds=600,
        idempotency_ttl_seconds=3600, llm_enabled=True, llm_api_key="",
        openrouter_api_key="", google_api_key="", llm_base_url="",
        llm_fast_model="gemini-3-flash-preview", llm_strong_model="minimax/minimax-m2.5:free",
        llm_timeout_seconds=1, llm_max_retries=3,
        llm_enable_self_eval=False, llm_gen_timeout_seconds=20,
        llm_gen_max_retries=1,
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


def test_fast_tier_falls_back_to_google_backup_model_first() -> None:
    settings = _make_settings(llm_max_retries=1, llm_fast_fallback_model="gemini-2.5-flash")
    gateway = LLMGateway(settings)
    fast_error = RuntimeError("403 PERMISSION_DENIED. Your API key was reported as leaked")
    fast_primary = _AlwaysFailModel(fast_error)
    fast_backup = _SuccessModel('{"quality_score": 7, "uncovered_areas": ["edge case"]}')
    strong = _SuccessModel('{"quality_score": 9, "uncovered_areas": []}')

    gateway._fast = fast_primary
    gateway._fast_fallback = fast_backup
    gateway._strong = strong

    result = gateway.invoke_text(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert result == '{"quality_score": 7, "uncovered_areas": ["edge case"]}'
    assert fast_primary.calls == 1
    assert fast_backup.calls == 1
    assert strong.calls == 0


def test_fast_tier_missing_primary_uses_google_backup_then_skips_strong_on_success() -> None:
    settings = _make_settings(llm_max_retries=1, llm_fast_fallback_model="gemini-2.5-flash")
    gateway = LLMGateway(settings)
    fast_backup = _SuccessModel('{"quality_score": 6, "uncovered_areas": []}')
    strong = _SuccessModel('{"quality_score": 9, "uncovered_areas": []}')

    gateway._fast = None
    gateway._fast_fallback = fast_backup
    gateway._strong = strong

    result = gateway.invoke_text(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert result == '{"quality_score": 6, "uncovered_areas": []}'
    assert fast_backup.calls == 1
    assert strong.calls == 0


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


def test_fast_tier_fallback_to_strong_failure_returns_local_fallback() -> None:
    settings = _make_settings(llm_max_retries=1)
    gateway = LLMGateway(settings)
    fast_error = RuntimeError("403 PERMISSION_DENIED. Your API key was reported as leaked")
    strong_error = RuntimeError("model_not_found: does not exist or you do not have access")
    fast = _AlwaysFailModel(fast_error)
    strong = _AlwaysFailModel(strong_error)

    gateway._fast = fast
    gateway._strong = strong

    payload = gateway.invoke_json(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert payload["target_framework"] == "unspecified"
    assert payload["test_type"] == "mixed"
    assert fast.calls == 1
    assert strong.calls == 1


def test_fast_tier_primary_and_backup_and_strong_fail_returns_local_fallback() -> None:
    settings = _make_settings(llm_max_retries=1, llm_fast_fallback_model="gemini-2.5-flash")
    gateway = LLMGateway(settings)
    fast_error = RuntimeError("403 PERMISSION_DENIED. Your API key was reported as leaked")
    backup_error = RuntimeError("model_not_found: does not exist or you do not have access")
    strong_error = RuntimeError("model_not_found: does not exist or you do not have access")
    fast_primary = _AlwaysFailModel(fast_error)
    fast_backup = _AlwaysFailModel(backup_error)
    strong = _AlwaysFailModel(strong_error)

    gateway._fast = fast_primary
    gateway._fast_fallback = fast_backup
    gateway._strong = strong

    payload = gateway.invoke_json(
        "You are an intent classifier for software test generation",
        "prompt",
        tier="fast",
    )

    assert payload["target_framework"] == "unspecified"
    assert payload["test_type"] == "mixed"
    assert fast_primary.calls == 1
    assert fast_backup.calls == 1
    assert strong.calls == 1


def test_strong_tier_non_retryable_falls_back_to_fast() -> None:
    settings = _make_settings(llm_max_retries=1)
    gateway = LLMGateway(settings)
    strong_error = RuntimeError("model_not_found: does not exist or you do not have access")
    strong = _AlwaysFailModel(strong_error)
    fast = _SuccessModel("def test_ok():\n    assert True")

    gateway._strong = strong
    gateway._fast = fast

    result = gateway.invoke_text(
        "You are a senior test generator",
        "Generate tests",
        tier="strong",
    )

    assert "test_ok" in result
    assert strong.calls == 1
    assert fast.calls == 1
