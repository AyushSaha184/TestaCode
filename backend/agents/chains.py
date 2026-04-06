from __future__ import annotations

from backend.agents.llm_gateway import LLMGateway
from backend.agents.prompts import (
	build_correction_prompts,
	build_generation_prompts,
	build_self_eval_prompts,
)
from backend.agents.tools import _strip_code_fences, validate_generated_code
from backend.core.config import Settings
from backend.util.logger import get_logger
from backend.schemas import UnifiedContext

logger = get_logger(__name__)

_SELF_EVAL_FALLBACK_SCORE = 7
_SELF_EVAL_FALLBACK_UNCOVERED: list[str] = []


class TestGenerationChain:
	def __init__(self, llm: LLMGateway, settings: Settings) -> None:
		self.llm = llm
		self.settings = settings

	def run_generation(self, context: UnifiedContext) -> str:
		logger.info("generation_call_started", extra={"step": "generation", "status": "processing"})
		system_prompt, user_prompt = build_generation_prompts(context)
		text = self.llm.invoke_text(
			system_prompt,
			user_prompt,
			tier="strong",
			timeout_override=self.settings.llm_gen_timeout_seconds,
			max_retries_override=self.settings.llm_gen_max_retries,
		)
		result = _strip_code_fences(text)
		logger.info("generation_call_completed", extra={"step": "generation", "status": "ok"})
		return result

	def run_validation_and_correction(self, context: UnifiedContext, generated_code: str) -> tuple[str, list[str]]:
		warnings: list[str] = []
		candidate = generated_code
		max_attempts = 3

		for attempt in range(1, max_attempts + 1):
			valid, error_text = validate_generated_code(context.detected_language, candidate)
			logger.info(
				"validation_attempt",
				extra={
					"step": "validation",
					"attempt": attempt,
					"status": "ok" if valid else "failed",
				},
			)
			if valid:
				if error_text:
					warnings.append(error_text)
				return candidate, warnings

			if attempt == max_attempts:
				warnings.append(f"Validation failed after retries: {error_text}")
				return candidate, warnings

			warnings.append(f"Validation retry {attempt}: {error_text}")
			logger.info(
				"correction_call_started",
				extra={"step": "correction", "attempt": attempt, "status": "processing"},
			)
			system_prompt, user_prompt = build_correction_prompts(
				context.detected_language.value,
				candidate,
				error_text or "unknown syntax error",
			)
			candidate = self.llm.invoke_text(system_prompt, user_prompt, tier="fast")
			candidate = _strip_code_fences(candidate)
			logger.info(
				"correction_call_completed",
				extra={"step": "correction", "attempt": attempt, "status": "ok"},
			)

		return candidate, warnings

	def run_self_evaluation(self, context: UnifiedContext, generated_code: str) -> tuple[int, list[str]]:
		if not self.settings.llm_enable_self_eval:
			logger.info("self_eval_skipped", extra={"step": "self_eval", "status": "disabled"})
			return _SELF_EVAL_FALLBACK_SCORE, list(_SELF_EVAL_FALLBACK_UNCOVERED)

		logger.info("self_eval_started", extra={"step": "self_eval", "status": "processing"})
		system_prompt, user_prompt = build_self_eval_prompts(context, generated_code)
		payload = self.llm.invoke_json(system_prompt, user_prompt, tier="fast")
		quality = int(payload.get("quality_score", 0))
		uncovered_areas = [str(item) for item in payload.get("uncovered_areas", [])]
		logger.info("self_eval_completed", extra={"step": "self_eval", "status": "ok"})
		return max(0, min(10, quality)), uncovered_areas
