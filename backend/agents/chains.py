from __future__ import annotations

from backend.agents.llm_gateway import LLMGateway
from backend.agents.prompts import (
	build_analysis_prompts,
	build_correction_prompts,
	build_generation_prompts,
	build_self_eval_prompts,
)
from backend.agents.tools import validate_generated_code
from backend.core.logger import get_logger
from backend.schemas import UnifiedContext

logger = get_logger(__name__)


class TestGenerationChain:
	def __init__(self, llm: LLMGateway) -> None:
		self.llm = llm

	def run_analysis(self, context: UnifiedContext) -> str:
		logger.info("analysis_call_started", extra={"step": "analysis", "status": "processing"})
		system_prompt, user_prompt = build_analysis_prompts(context)
		text = self.llm.invoke_text(system_prompt, user_prompt, tier="strong")
		logger.info("analysis_call_completed", extra={"step": "analysis", "status": "ok"})
		return text

	def run_generation(self, context: UnifiedContext, analysis_text: str) -> str:
		logger.info("generation_call_started", extra={"step": "generation", "status": "processing"})
		system_prompt, user_prompt = build_generation_prompts(context, analysis_text)
		text = self.llm.invoke_text(system_prompt, user_prompt, tier="strong")
		logger.info("generation_call_completed", extra={"step": "generation", "status": "ok"})
		return text

	def run_validation_and_correction(self, context: UnifiedContext, generated_code: str) -> tuple[str, list[str]]:
		warnings: list[str] = []
		candidate = generated_code

		for attempt in range(0, 3):
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
				return candidate, warnings

			if attempt >= 2:
				warnings.append(f"Validation failed after retries: {error_text}")
				return candidate, warnings

			warnings.append(f"Validation retry {attempt + 1}: {error_text}")
			logger.info(
				"correction_call_started",
				extra={"step": "correction", "attempt": attempt + 1, "status": "processing"},
			)
			system_prompt, user_prompt = build_correction_prompts(
				context.detected_language.value,
				candidate,
				error_text or "unknown syntax error",
			)
			candidate = self.llm.invoke_text(system_prompt, user_prompt, tier="fast")
			logger.info(
				"correction_call_completed",
				extra={"step": "correction", "attempt": attempt + 1, "status": "ok"},
			)

		return candidate, warnings

	def run_self_evaluation(self, context: UnifiedContext, generated_code: str) -> tuple[int, list[str]]:
		logger.info("self_eval_started", extra={"step": "self_eval", "status": "processing"})
		system_prompt, user_prompt = build_self_eval_prompts(context, generated_code)
		payload = self.llm.invoke_json(system_prompt, user_prompt, tier="fast")
		quality = int(payload.get("quality_score", 0))
		uncovered_areas = [str(item) for item in payload.get("uncovered_areas", [])]
		logger.info("self_eval_completed", extra={"step": "self_eval", "status": "ok"})
		return max(0, min(10, quality)), uncovered_areas
