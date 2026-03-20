from __future__ import annotations

import hashlib

from backend.agents.llm_gateway import LLMGateway
from backend.core.cache import CacheBackend, TTLCache
from backend.core.logger import get_logger
from backend.schemas import IntentClassification, Language

logger = get_logger(__name__)


class PromptIntentClassifier:
	def __init__(
		self,
		llm: LLMGateway,
		ttl_seconds: int,
		cache: CacheBackend[str, IntentClassification] | None = None,
	) -> None:
		self.llm = llm
		self.cache = cache or TTLCache[str, IntentClassification](ttl_seconds)

	def classify(self, prompt: str, language: Language, code: str) -> tuple[IntentClassification, list[str]]:
		code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
		cache_key = f"{prompt}:{language.value}:{code_hash}"
		cached = self.cache.get(cache_key)
		if cached is not None:
			logger.info("intent_classifier_cache_hit", extra={"step": "intent", "status": "ok"})
			warnings = ["Low confidence intent classification; generation continued"] if cached.confidence < 0.55 else []
			return cached, warnings

		system_prompt = (
			"You are an intent classifier for software test generation. Return strict JSON with keys: "
			"test_type(unit|integration|edge|mixed), target_scope, target_framework(pytest|unittest|jest|mocha|unspecified), "
			"special_requirements(list of strings), confidence(float 0..1)."
		)
		user_prompt = f"Language: {language.value}\nPrompt: {prompt}\nCode:\n{code}"
		payload = self.llm.invoke_json(system_prompt, user_prompt, tier="fast")
		intent = IntentClassification(**payload)
		self.cache.set(cache_key, intent)

		warnings: list[str] = []
		if intent.confidence < 0.55:
			warnings.append("Low confidence intent classification; generation continued")

		logger.info(
			"intent_classifier_completed",
			extra={"step": "intent", "status": "ok", "attempt": 1},
		)
		return intent, warnings

	def classify_for_session(self, session_id: str, prompt: str, language: Language, code: str) -> tuple[IntentClassification, list[str]]:
		code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
		cache_key = f"{session_id}:{prompt}:{language.value}:{code_hash}"
		cached = self.cache.get(cache_key)
		if cached is not None:
			logger.info("intent_classifier_cache_hit", extra={"step": "intent", "status": "ok"})
			warnings = ["Low confidence intent classification; generation continued"] if cached.confidence < 0.55 else []
			return cached, warnings

		system_prompt = (
			"You are an intent classifier for software test generation. Return strict JSON with keys: "
			"test_type(unit|integration|edge|mixed), target_scope, target_framework(pytest|unittest|jest|mocha|unspecified), "
			"special_requirements(list of strings), confidence(float 0..1)."
		)
		user_prompt = f"Language: {language.value}\nPrompt: {prompt}\nCode:\n{code}"
		payload = self.llm.invoke_json(system_prompt, user_prompt, tier="fast")
		intent = IntentClassification(**payload)
		self.cache.set(cache_key, intent)

		warnings: list[str] = []
		if intent.confidence < 0.55:
			warnings.append("Low confidence intent classification; generation continued")

		logger.info(
			"intent_classifier_completed",
			extra={"step": "intent", "status": "ok", "attempt": 1},
		)
		return intent, warnings
