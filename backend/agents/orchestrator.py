from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from backend.agents.chains import TestGenerationChain
from backend.agents.prompts import build_analysis_summary
from backend.core.cache import CacheBackend, TTLCache
from backend.core.exceptions import AppError
from backend.util.logger import get_logger
from backend.input.handlers import InputProcessingService
from backend.repositories.generation_repository import GenerationRepository
from backend.services.file_output_service import FileOutputResult, FileOutputService
from backend.schemas import (
	GenerationRequest,
	GenerationResponse,
	InputMode,
	JobStatus,
	JobStatusView,
	Language,
	RerunResult,
	UnifiedContext,
)

logger = get_logger(__name__)


@contextmanager
def _stage_timer(stage: str):
	"""Context manager that logs wall-clock duration for a pipeline stage."""
	t0 = time.monotonic()
	try:
		yield
	finally:
		duration_ms = round((time.monotonic() - t0) * 1000, 1)
		logger.info("stage_timing", extra={"stage": stage, "duration_ms": duration_ms, "status": "ok"})


class GenerationOrchestrator:
	def __init__(
		self,
		repository: GenerationRepository,
		input_service: InputProcessingService,
		chain: TestGenerationChain,
		file_output_service: FileOutputService,
		idempotency_ttl_seconds: int,
		idempotency_cache: CacheBackend[str, UUID] | None = None,
	) -> None:
		self.repository = repository
		self.input_service = input_service
		self.chain = chain
		self.file_output_service = file_output_service
		self.idempotency_cache = idempotency_cache or TTLCache[str, UUID](idempotency_ttl_seconds)

	def generate(self, request: GenerationRequest, initial_warnings: list[str], idempotency_key: str | None) -> GenerationResponse:
		request_t0 = time.monotonic()
		scoped_idempotency_key = f"{request.session_id}:{idempotency_key}" if idempotency_key else None
		if scoped_idempotency_key:
			cached_job_id = self.idempotency_cache.get(scoped_idempotency_key)
			if cached_job_id:
				existing = self.repository.get_job(cached_job_id, session_id=request.session_id)
				if existing and existing.generated_test_code is not None and existing.quality_score is not None:
					logger.info(
						"idempotency_cache_hit",
						extra={"step": "generation", "job_id": str(existing.id), "status": "ok"},
					)
					return GenerationResponse(
						job_id=existing.id,
						detected_language=existing.detected_language,
						generated_test_code=existing.generated_test_code,
						quality_score=existing.quality_score,
						uncovered_areas=existing.uncovered_areas,
						warnings=existing.warnings,
						framework_used=existing.framework_used or "unspecified",
						source_file_path=existing.source_file_path,
						output_test_path=existing.output_test_path,
						output_metadata_path=existing.output_metadata_path,
					)

		job_id = self.repository.create_job(request, status=JobStatus.queued)
		if scoped_idempotency_key:
			self.idempotency_cache.set(scoped_idempotency_key, job_id)

		warnings = list(initial_warnings)
		file_result: FileOutputResult | None = None

		try:
			self.repository.update_job_processing(job_id)

			with _stage_timer("input_processing"):
				context = self.input_service.build_unified_context(request, warnings)

			with _stage_timer("generation"):
				generated_code = self.chain.run_generation(context)

			with _stage_timer("validation"):
				generated_code, validation_warnings = self.chain.run_validation_and_correction(context, generated_code)
			warnings.extend(validation_warnings)

			with _stage_timer("self_evaluation"):
				quality_score, uncovered_areas = self.chain.run_self_evaluation(context, generated_code)

			framework_used = _resolve_framework(context.classified_intent.target_framework.value, request.language.value)
			mock_warnings = _derive_mocking_warnings(context)
			warnings.extend(mock_warnings)

			classified_intent_payload: dict[str, Any] = {
				"intent": context.classified_intent.model_dump(mode="json"),
				"raw_code": context.raw_code,
				"function_metadata": [item.model_dump(mode="json") for item in context.function_metadata],
			}
			analysis_text = build_analysis_summary(context)

			self.repository.update_job_completed(
				job_id=job_id,
				classified_intent=classified_intent_payload,
				analysis_text=analysis_text,
				generated_test_code=generated_code,
				quality_score=quality_score,
				framework_used=framework_used,
				warnings=warnings,
				uncovered_areas=uncovered_areas,
			)

			local_test_file_path: str | None = None
			local_metadata_file_path: str | None = None
			with _stage_timer("file_output_local"):
				try:
					file_result = self.file_output_service.write_outputs(
						job_id=job_id,
						session_id=request.session_id,
						input_mode=request.input_mode,
						original_filename=request.filename,
						context=context,
						generated_test_code=generated_code,
						quality_score=quality_score,
						framework_used=framework_used,
						uncovered_areas=uncovered_areas,
					)
					warnings.extend(file_result.warnings)
					for warning in file_result.warnings:
						self.repository.append_warning(job_id, warning)
					local_test_file_path = file_result.local_test_file_path
					local_metadata_file_path = file_result.local_metadata_file_path
				except Exception as file_exc:
					warning = f"File output failed: {file_exc}"
					warnings.append(warning)
					self.repository.append_warning(job_id, warning)

			if file_result is not None:
				self.repository.update_file_outputs(
					job_id,
					source_file_path=None,
					output_test_path=local_test_file_path,
					output_metadata_path=local_metadata_file_path,
				)

			total_ms = round((time.monotonic() - request_t0) * 1000, 1)
			logger.info("stage_timing", extra={"stage": "total_request", "duration_ms": total_ms, "status": "ok"})

			return GenerationResponse(
				job_id=job_id,
				detected_language=context.detected_language,
				generated_test_code=generated_code,
				quality_score=quality_score,
				uncovered_areas=uncovered_areas,
				warnings=warnings,
				framework_used=framework_used,
				source_file_path=None,
				output_test_path=local_test_file_path if file_result else None,
				output_metadata_path=local_metadata_file_path if file_result else None,
			)
		except Exception as exc:
			warnings.append(f"Generation failed: {exc}")
			self.repository.update_job_failed(job_id, warnings)
			logger.exception(
				"generation_failed",
				extra={"job_id": str(job_id), "step": "generation", "status": "failed"},
			)
			raise

	def rerun(self, job_id: UUID, session_id: str) -> RerunResult:
		original = self.repository.get_job_record(job_id, session_id=session_id)
		if original is None:
			raise AppError("Job not found", status_code=404)

		classified = original.get("classified_intent") or {}
		raw_code = classified.get("raw_code")
		if not raw_code:
			raise AppError("Rerun unavailable: original code snapshot not found", status_code=400)

		intent_payload = classified.get("intent") or {}
		target_framework = (intent_payload.get("target_framework") or "unspecified")
		user_prompt = original.get("user_prompt") or "Rerun test generation"

		try:
			input_mode = InputMode(original["input_mode"])
			language = Language(original["detected_language"])
		except Exception as exc:
			raise AppError("Rerun unavailable: original job contains invalid input metadata", status_code=400) from exc

		regenerated_request = GenerationRequest(
			session_id=session_id,
			input_mode=input_mode,
			code_content=raw_code,
			filename=original.get("original_filename"),
			language=language,
			user_prompt=_build_rerun_prompt(
				base_prompt=user_prompt,
				target_framework=target_framework,
				feedback=None,
				previous_generated_code="",
			),
		)
		response = self.generate(regenerated_request, [], idempotency_key=None)

		return RerunResult(
			original_job_id=job_id,
			rerun_job_id=response.job_id,
			status=JobStatus.completed,
			quality_score=response.quality_score,
		)

	def get_status(self, job_id: UUID, session_id: str) -> JobStatusView:
		job = self.repository.get_job(job_id, session_id=session_id)
		if not job:
			raise AppError("Job not found", status_code=404)
		return JobStatusView(
			job_id=job.id,
			status=job.status,
		)


def _resolve_framework(requested: str, language: str) -> str:
	if requested != "unspecified":
		return requested
	if language == "python":
		return "pytest"
	if language in ("javascript", "typescript"):
		return "jest"
	if language == "java":
		return "junit"
	if language == "rust":
		return "cargo test"
	if language == "golang":
		return "go test"
	if language == "csharp":
		return "xunit"
	return "unspecified"


def _derive_mocking_warnings(context: UnifiedContext) -> list[str]:
	hints = sorted({hint for fn in context.function_metadata for hint in fn.dependency_hints})
	if not hints:
		return []
	joined = ", ".join(hints[:8])
	if context.detected_language.value == "python":
		return [f"Detected dependency candidates for patch/MagicMock: {joined}"]
	if context.detected_language.value in ("javascript", "typescript"):
		return [f"Detected dependency candidates for jest.mock: {joined}"]
	return [f"Detected dependency candidates: {joined}"]


def _build_rerun_prompt(
	*,
	base_prompt: str,
	target_framework: str,
	feedback,
	previous_generated_code: str,
) -> str:
	# Preserve the original user prompt exactly as provided.
	# Rerun should not append framework, feedback, or prior output text.
	_ = target_framework
	_ = feedback
	_ = previous_generated_code
	return base_prompt
