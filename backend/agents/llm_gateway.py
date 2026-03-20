from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from backend.core.config import Settings
from backend.core.logger import get_logger

logger = get_logger(__name__)
ModelTier = Literal["fast", "strong"]


class LLMGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fast = None
        self._strong = None

        if not settings.llm_enabled:
            return

        openrouter_key = settings.llm_api_key or settings.openrouter_api_key

        if settings.google_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._fast = ChatGoogleGenerativeAI(
                    model=settings.llm_fast_model,
                    google_api_key=settings.google_api_key,
                    temperature=0.2,
                )
                logger.info(
                    "llm_fast_provider_initialized",
                    extra={"step": "llm_init", "provider": "google", "model": settings.llm_fast_model},
                )
            except Exception:
                logger.exception(
                    "llm_fast_provider_failed",
                    extra={"step": "llm_init", "provider": "google", "model": settings.llm_fast_model},
                )

        if openrouter_key:
            try:
                from langchain_openai import ChatOpenAI

                kwargs: dict[str, Any] = {
                    "api_key": openrouter_key,
                    "timeout": settings.llm_timeout_seconds,
                }
                if settings.llm_base_url:
                    kwargs["base_url"] = settings.llm_base_url

                if self._fast is None:
                    self._fast = ChatOpenAI(model=settings.llm_fast_model, temperature=0.2, **kwargs)
                    logger.info(
                        "llm_fast_provider_initialized",
                        extra={"step": "llm_init", "provider": "openrouter", "model": settings.llm_fast_model},
                    )

                self._strong = ChatOpenAI(model=settings.llm_strong_model, temperature=0.2, **kwargs)
                logger.info(
                    "llm_strong_provider_initialized",
                    extra={"step": "llm_init", "provider": "openrouter", "model": settings.llm_strong_model},
                )
            except Exception:
                logger.exception(
                    "llm_openrouter_provider_failed",
                    extra={"step": "llm_init", "provider": "openrouter"},
                )

    def _model(self, tier: ModelTier):
        return self._fast if tier == "fast" else self._strong

    def invoke_text(self, system_prompt: str, user_prompt: str, tier: ModelTier) -> str:
        model = self._model(tier)
        model_name = self.settings.llm_fast_model if tier == "fast" else self.settings.llm_strong_model

        for attempt in range(1, self.settings.llm_max_retries + 1):
            logger.info(
                "llm_call_started",
                extra={"step": "llm_call", "attempt": attempt, "model": model_name},
            )

            try:
                if model is None:
                    return self._fallback(system_prompt, user_prompt)

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        model.invoke,
                        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
                    )
                    response = future.result(timeout=self.settings.llm_timeout_seconds)

                text = getattr(response, "content", "")
                if isinstance(text, list):
                    text = "\n".join(str(item) for item in text)

                logger.info(
                    "llm_call_completed",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "ok"},
                )
                return str(text)
            except TimeoutError:
                logger.warning(
                    "llm_call_timeout",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "timeout"},
                )
            except Exception:
                logger.exception(
                    "llm_call_failed",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "error"},
                )

            if attempt < self.settings.llm_max_retries:
                time.sleep(min(2 ** (attempt - 1), 6))

        raise RuntimeError("LLM invocation failed after retries")

    def invoke_json(self, system_prompt: str, user_prompt: str, tier: ModelTier) -> dict[str, Any]:
        text = self.invoke_text(system_prompt, user_prompt, tier=tier)
        text = text.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def _fallback(self, system_prompt: str, user_prompt: str) -> str:
        if "intent classifier" in system_prompt.lower():
            return json.dumps(
                {
                    "test_type": "mixed",
                    "target_scope": "all",
                    "target_framework": "unspecified",
                    "special_requirements": [],
                    "confidence": 0.45,
                }
            )

        if "javascript/typescript parser" in system_prompt.lower():
            return json.dumps({"functions": []})

        if "self-evaluate" in system_prompt.lower():
            return json.dumps(
                {
                    "quality_score": 4,
                    "uncovered_areas": ["LLM disabled, limited evaluation"],
                }
            )

        if "correction" in system_prompt.lower():
            return user_prompt

        return "# LLM disabled. Configure LLM_ENABLED=true and LLM_API_KEY for generated test content.\n"
