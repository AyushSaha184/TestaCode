from __future__ import annotations

from unittest.mock import MagicMock

from backend.agents.chains import TestGenerationChain
from backend.core.config import Settings
from backend.schemas import (
    IntentClassification,
    Language,
    TestType,
    TargetFramework,
    UnifiedContext,
    FunctionMetadata,
    ParameterMetadata,
)


def _make_context(code: str = "def add(a, b): return a + b") -> UnifiedContext:
    return UnifiedContext(
        raw_code=code,
        detected_language=Language.python,
        function_metadata=[
            FunctionMetadata(
                name="add",
                params=[
                    ParameterMetadata(name="a", type_annotation="int"),
                    ParameterMetadata(name="b", type_annotation="int"),
                ],
                return_annotation="int",
                docstring=None,
                decorators=[],
                dependency_hints=[],
            )
        ],
        classified_intent=IntentClassification(
            test_type=TestType.unit,
            target_scope="all",
            target_framework=TargetFramework.pytest,
            special_requirements=[],
            confidence=0.9,
        ),
        original_prompt="Generate unit tests",
        warnings=[],
    )


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
        openrouter_api_key="", google_api_key="",
        cerebras_api_key="", llm_base_url="",
        llm_fast_model="gpt-4o-mini", llm_strong_model="gpt-4.1",
        llm_timeout_seconds=25, llm_max_retries=3,
        llm_enable_self_eval=False, llm_gen_timeout_seconds=20,
        llm_gen_max_retries=1,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_generation_without_analysis():
    """After collapsing, generation succeeds without a prior run_analysis call."""
    settings = _make_settings()
    mock_llm = MagicMock()
    mock_llm.invoke_text.return_value = "def test_add():\n    assert add(1, 2) == 3"
    chain = TestGenerationChain(mock_llm, settings)
    context = _make_context()

    result = chain.run_generation(context)

    assert "test_add" in result
    mock_llm.invoke_text.assert_called_once()
    call_kwargs = mock_llm.invoke_text.call_args
    assert call_kwargs.kwargs.get("timeout_override") == settings.llm_gen_timeout_seconds
    assert call_kwargs.kwargs.get("max_retries_override") == settings.llm_gen_max_retries


def test_self_eval_disabled_returns_fallback():
    """When self-eval is disabled, returns deterministic fallback without LLM call."""
    settings = _make_settings(llm_enable_self_eval=False)
    mock_llm = MagicMock()
    chain = TestGenerationChain(mock_llm, settings)
    context = _make_context()

    score, uncovered = chain.run_self_evaluation(context, "def test_x(): pass")

    assert score == 7
    assert uncovered == []
    mock_llm.invoke_json.assert_not_called()


def test_self_eval_enabled_calls_llm():
    """When self-eval is enabled, it calls the LLM and parses the result."""
    settings = _make_settings(llm_enable_self_eval=True)
    mock_llm = MagicMock()
    mock_llm.invoke_json.return_value = {
        "quality_score": 8,
        "uncovered_areas": ["edge case"],
    }
    chain = TestGenerationChain(mock_llm, settings)
    context = _make_context()

    score, uncovered = chain.run_self_evaluation(context, "def test_x(): pass")

    assert score == 8
    assert uncovered == ["edge case"]
    mock_llm.invoke_json.assert_called_once()


def test_chain_has_no_run_analysis_method():
    """Verify run_analysis was removed from the chain."""
    settings = _make_settings()
    mock_llm = MagicMock()
    chain = TestGenerationChain(mock_llm, settings)
    assert not hasattr(chain, "run_analysis")
