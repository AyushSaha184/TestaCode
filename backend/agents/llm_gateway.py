from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ExecTimeoutError
from types import SimpleNamespace
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from backend.core.config import Settings
from backend.util.logger import get_logger

logger = get_logger(__name__)
ModelTier = Literal["fast", "strong"]


class _CerebrasChatModel:
    def __init__(self, api_key: str, model: str) -> None:
        from cerebras.cloud.sdk import Cerebras

        self._client = Cerebras(api_key=api_key)
        self._model = model

    def invoke(self, messages: list[SystemMessage | HumanMessage]) -> Any:
        payload: list[dict[str, str]] = []
        for message in messages:
            if isinstance(message, SystemMessage):
                role = "system"
            else:
                role = "user"
            payload.append({"role": role, "content": str(message.content)})

        completion = self._client.chat.completions.create(
            messages=payload,
            model=self._model,
            temperature=0.2,
        )
        text = completion.choices[0].message.content if completion.choices else ""
        return SimpleNamespace(content=text)


class LLMGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fast = None
        self._fast_fallback = None
        self._strong = None
        self._executor = ThreadPoolExecutor(max_workers=4)

        if not settings.llm_enabled:
            return

        cerebras_api_key = settings.cerebras_api_key or settings.llm_api_key

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

            fallback_model = (settings.llm_fast_fallback_model or "").strip()
            if fallback_model and fallback_model != settings.llm_fast_model:
                try:
                    self._fast_fallback = ChatGoogleGenerativeAI(
                        model=fallback_model,
                        google_api_key=settings.google_api_key,
                        temperature=0.2,
                    )
                    logger.info(
                        "llm_fast_fallback_provider_initialized",
                        extra={"step": "llm_init", "provider": "google", "model": fallback_model},
                    )
                except Exception:
                    logger.exception(
                        "llm_fast_fallback_provider_failed",
                        extra={"step": "llm_init", "provider": "google", "model": fallback_model},
                    )

        if cerebras_api_key:
            try:
                self._strong = _CerebrasChatModel(
                    api_key=cerebras_api_key,
                    model=settings.llm_strong_model,
                )
                logger.info(
                    "llm_strong_provider_initialized",
                    extra={"step": "llm_init", "provider": "cerebras", "model": settings.llm_strong_model},
                )
            except Exception:
                logger.exception(
                    "llm_cerebras_provider_failed",
                    extra={"step": "llm_init", "provider": "cerebras"},
                )

    def _model(self, tier: ModelTier):
        return self._fast if tier == "fast" else self._strong

    @staticmethod
    def _is_non_retryable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        non_retryable_markers = (
            "permission_denied",
            "api key was reported as leaked",
            "unauthorized",
            "invalid api key",
            "authentication",
            "status code: 401",
            "status code: 403",
            "model_not_found",
            "does not exist or you do not have access",
        )
        return any(marker in message for marker in non_retryable_markers)

    def invoke_text(
        self,
        system_prompt: str,
        user_prompt: str,
        tier: ModelTier,
        timeout_override: int | None = None,
        max_retries_override: int | None = None,
        _allow_tier_fallback: bool = True,
        _allow_fast_model_fallback: bool = True,
        _model_override: Any | None = None,
        _model_name_override: str | None = None,
    ) -> str:
        model = _model_override if _model_override is not None else self._model(tier)
        model_name = (
            _model_name_override
            if _model_name_override is not None
            else (self.settings.llm_fast_model if tier == "fast" else self.settings.llm_strong_model)
        )
        effective_timeout = timeout_override if timeout_override is not None else self.settings.llm_timeout_seconds
        effective_retries = max_retries_override if max_retries_override is not None else self.settings.llm_max_retries
        last_error: Exception | None = None

        for attempt in range(1, effective_retries + 1):
            logger.info(
                "llm_call_started",
                extra={"step": "llm_call", "attempt": attempt, "model": model_name},
            )

            try:
                if model is None:
                    if tier == "strong" and _allow_tier_fallback and self._fast is not None:
                        logger.warning(
                            "llm_strong_fallback_to_fast",
                            extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                        )
                        return self.invoke_text(
                            system_prompt,
                            user_prompt,
                            tier="fast",
                            timeout_override=timeout_override,
                            max_retries_override=max_retries_override,
                            _allow_tier_fallback=False,
                        )
                    if tier == "fast":
                        logger.warning(
                            "llm_fast_model_missing",
                            extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                        )
                        break
                    return self._fallback(system_prompt, user_prompt)

                future = self._executor.submit(
                    model.invoke,
                    [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
                )
                response = future.result(timeout=effective_timeout)

                content = getattr(response, "content", "")
                if isinstance(content, list):
                    # Gemini 3 thinking models return a list of typed parts:
                    # [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "..."}]
                    # We must extract only "text" parts — str(item) on dicts produces
                    # Python single-quoted strings which break JSON parsing.
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    text = "\n".join(text_parts)
                else:
                    text = str(content)

                logger.info(
                    "llm_call_completed",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "ok"},
                )
                return text
            except ExecTimeoutError as exc:
                last_error = exc
                try:
                    future.cancel()
                except Exception:
                    pass
                logger.warning(
                    "llm_call_timeout",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "timeout"},
                )
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "llm_call_failed",
                    extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "error"},
                )
                if self._is_non_retryable_error(exc):
                    if tier == "strong":
                        # Prevent repeated hard-fail calls to an invalid/unavailable strong model.
                        self._strong = None
                    logger.warning(
                        "llm_call_non_retryable_error",
                        extra={"step": "llm_call", "attempt": attempt, "model": model_name, "status": "terminal"},
                    )
                    break

            if attempt < effective_retries:
                time.sleep(min(2 ** (attempt - 1), 6))

        if tier == "fast":
            if _allow_fast_model_fallback and _allow_tier_fallback and model is self._fast and self._fast_fallback is not None:
                fallback_model_name = self.settings.llm_fast_fallback_model
                logger.warning(
                    "llm_fast_fallback_to_google_backup",
                    extra={"step": "llm_call", "status": "fallback", "from_model": model_name, "to_model": fallback_model_name},
                )
                return self.invoke_text(
                    system_prompt,
                    user_prompt,
                    tier="fast",
                    timeout_override=timeout_override,
                    max_retries_override=max_retries_override,
                    _allow_tier_fallback=True,
                    _allow_fast_model_fallback=False,
                    _model_override=self._fast_fallback,
                    _model_name_override=fallback_model_name,
                )

            if _allow_tier_fallback and self._strong is not None and self._strong is not model:
                logger.warning(
                    "llm_fast_fallback_to_strong",
                    extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                )
                try:
                    return self.invoke_text(
                        system_prompt,
                        user_prompt,
                        tier="strong",
                        timeout_override=timeout_override,
                        max_retries_override=max_retries_override,
                        _allow_tier_fallback=False,
                    )
                except Exception:
                    logger.warning(
                        "llm_fast_fallback_to_strong_failed_local_fallback",
                        extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                    )
                    return self._fallback(system_prompt, user_prompt)
            logger.warning(
                "llm_fast_fallback_local",
                extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
            )
            return self._fallback(system_prompt, user_prompt)

        if not _allow_tier_fallback:
            logger.warning(
                "llm_strong_fallback_local",
                extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
            )
            return self._fallback(system_prompt, user_prompt)

        if tier == "strong":
            if self._fast is not None:
                logger.warning(
                    "llm_strong_fallback_to_fast_after_failure",
                    extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                )
                try:
                    return self.invoke_text(
                        system_prompt,
                        user_prompt,
                        tier="fast",
                        timeout_override=timeout_override,
                        max_retries_override=max_retries_override,
                        _allow_tier_fallback=False,
                    )
                except Exception:
                    logger.warning(
                        "llm_strong_fallback_to_fast_failed_local_fallback",
                        extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
                    )
            logger.warning(
                "llm_strong_fallback_local",
                extra={"step": "llm_call", "status": "fallback", "from_model": model_name},
            )
            return self._fallback(system_prompt, user_prompt)

        raise RuntimeError("LLM invocation failed after retries") from last_error

    def invoke_json(
        self,
        system_prompt: str,
        user_prompt: str,
        tier: ModelTier,
        timeout_override: int | None = None,
        max_retries_override: int | None = None,
    ) -> dict[str, Any]:
        text = self.invoke_text(
            system_prompt, user_prompt, tier=tier,
            timeout_override=timeout_override, max_retries_override=max_retries_override,
        )
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

        return "# LLM unavailable. Configure GOOGLE_API_KEY and/or CEREBRAS_API_KEY for generated test content.\n"
