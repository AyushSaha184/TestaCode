from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.agents.chains import TestGenerationChain
from backend.agents.prompts import build_analysis_summary
from backend.core.cache import CacheBackend, TTLCache
from backend.core.exceptions import AppError
from backend.core.logger import get_logger
from backend.input.handlers import InputProcessingService
from backend.repositories.generation_repository import GenerationRepository
from backend.services.file_output_service import FileOutputResult, FileOutputService
from backend.services.git_integration_service import GitIntegrationService
from backend.schemas import (
	GenerationRequest,
	GenerationResponse,
	JobStatus,
	JobStatusView,
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
		git_integration_service: GitIntegrationService,
		idempotency_ttl_seconds: int,
		idempotency_cache: CacheBackend[str, UUID] | None = None,
	) -> None:
		self.repository = repository
		self.input_service = input_service
		self.chain = chain
		self.file_output_service = file_output_service
		self.git_integration_service = git_integration_service
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
						source_file_url=existing.source_file_url,
						output_test_path=existing.output_test_path,
						output_metadata_path=existing.output_metadata_path,
						output_test_url=existing.output_test_url,
						output_metadata_url=existing.output_metadata_url,
						commit_sha=existing.commit_sha,
						ci_status=existing.ci_status,
						ci_conclusion=existing.ci_conclusion,
						ci_run_url=existing.ci_run_url,
						ci_run_id=existing.ci_run_id,
					)

		job_id = self.repository.create_job(request, status=JobStatus.queued)
		if scoped_idempotency_key:
			self.idempotency_cache.set(scoped_idempotency_key, job_id)

		warnings = list(initial_warnings)
		file_result: FileOutputResult | None = None
		commit_sha: str | None = None
		ci_status = "not_triggered"
		ci_conclusion: str | None = None
		ci_run_url: str | None = None
		ci_run_id: str | None = None

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
			feature_name: str | None = None
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
					feature_name = file_result.feature_name
				except Exception as file_exc:
					warning = f"File output failed: {file_exc}"
					warnings.append(warning)
					self.repository.append_warning(job_id, warning)
					self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="file_write_failed")
					ci_status = "ci_unavailable"
					ci_conclusion = "file_write_failed"

			storage_deferred = bool(file_result and feature_name and self.file_output_service.is_storage_configured())
			source_upload_deferred = bool(
				request.input_mode.value == "upload"
				and request.filename
				and self.file_output_service.is_storage_configured()
			)
			git_deferred = bool(
				request.auto_commit_enabled
				and feature_name
				and local_test_file_path
				and local_metadata_file_path
			)

			if file_result is not None and not storage_deferred:
				self.repository.update_file_outputs(
					job_id,
					source_file_path=None,
					source_file_url=None,
					output_test_path=local_test_file_path,
					output_metadata_path=local_metadata_file_path,
					output_test_url=None,
					output_metadata_url=None,
					ci_status="file_written",
				)
				ci_status = "file_written"

			if storage_deferred or source_upload_deferred or git_deferred:
				self.repository.update_ci_state(job_id, ci_status="deferred")
				ci_status = "deferred"
				self._defer_post_processing(
					job_id=job_id,
					request=request,
					context=context,
					feature_name=feature_name,
					local_test_file_path=local_test_file_path,
					local_metadata_file_path=local_metadata_file_path,
					generated_test_code=generated_code,
					quality_score=quality_score,
					framework_used=framework_used,
					uncovered_areas=uncovered_areas,
				)
			else:
				if request.auto_commit_enabled and file_result is None:
					ci_status = "ci_unavailable"
					self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="commit_skipped")
				else:
					preserved_statuses = {"file_written", "ci_unavailable"}
					ci_status = ci_status if ci_status in preserved_statuses else "not_triggered"
					self.repository.update_ci_state(job_id, ci_status=ci_status)

			self.repository.record_test_run(
				job_id=job_id,
				pass_count=max(1, quality_score // 2),
				fail_count=max(0, (10 - quality_score) // 3),
				error_count=0,
				coverage_percentage=float(min(95, max(20, quality_score * 10))),
				raw_results={"quality_score": quality_score, "uncovered_areas": uncovered_areas},
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
				source_file_url=None,
				output_test_path=local_test_file_path if file_result and not storage_deferred else None,
				output_metadata_path=local_metadata_file_path if file_result and not storage_deferred else None,
				output_test_url=None,
				output_metadata_url=None,
				commit_sha=commit_sha,
				ci_status=ci_status,
				ci_conclusion=ci_conclusion,
				ci_run_url=ci_run_url,
				ci_run_id=ci_run_id,
			)
		except Exception as exc:
			warnings.append(f"Generation failed: {exc}")
			self.repository.update_job_failed(job_id, warnings)
			logger.exception(
				"generation_failed",
				extra={"job_id": str(job_id), "step": "generation", "status": "failed"},
			)
			raise

	def _defer_post_processing(
		self,
		job_id: UUID,
		request: GenerationRequest,
		context: UnifiedContext,
		feature_name: str | None,
		local_test_file_path: str | None,
		local_metadata_file_path: str | None,
		generated_test_code: str,
		quality_score: int,
		framework_used: str,
		uncovered_areas: list[str],
	) -> None:
		def _run():
			try:
				current_source_path: str | None = None
				current_source_url: str | None = None
				current_test_path: str | None = None
				current_metadata_path: str | None = None
				current_test_url: str | None = None
				current_metadata_url: str | None = None
				final_ci_status = "file_written"
				final_ci_conclusion: str | None = None

				if request.input_mode.value == "upload" and request.filename and self.file_output_service.is_storage_configured():
					with _stage_timer("storage_source_upload"):
						current_source_path, current_source_url = self.file_output_service.upload_source_file(
							session_id=request.session_id,
							original_filename=request.filename,
							detected_language=request.language,
							source_code=request.code_content,
						)

				if feature_name and self.file_output_service.is_storage_configured():
					with _stage_timer("storage_artifact_upload"):
						(
							current_test_path,
							current_metadata_path,
							current_test_url,
							current_metadata_url,
							storage_warnings,
						) = self.file_output_service.upload_output_artifacts(
							session_id=request.session_id,
							detected_language=context.detected_language,
							feature_name=feature_name,
							generated_test_code=generated_test_code,
							metadata_payload=_build_metadata_payload(
								job_id=job_id,
								request=request,
								context=context,
								quality_score=quality_score,
								framework_used=framework_used,
								uncovered_areas=uncovered_areas,
							),
						)
					for warning in storage_warnings:
						self.repository.append_warning(job_id, warning)
					if storage_warnings:
						final_ci_status = "artifact_partial"
						final_ci_conclusion = "storage_upload_partial"

				if current_test_path or current_metadata_path or current_source_path or current_source_url:
					self.repository.update_file_outputs(
						job_id,
						source_file_path=current_source_path,
						source_file_url=current_source_url,
						output_test_path=current_test_path,
						output_metadata_path=current_metadata_path,
						output_test_url=current_test_url,
						output_metadata_url=current_metadata_url,
						ci_status=final_ci_status,
					)

				if request.auto_commit_enabled and feature_name and local_test_file_path and local_metadata_file_path:
					with _stage_timer("git_integration"):
						git_result = self.git_integration_service.commit_generated_outputs(
							job_id=job_id,
							feature_name=feature_name,
							test_file_path=local_test_file_path,
							metadata_file_path=local_metadata_file_path,
						)
					if git_result.warning:
						self.repository.append_warning(job_id, git_result.warning)
					if git_result.committed:
						self.repository.update_commit_state(
							job_id,
							commit_sha=git_result.commit_sha,
							ci_status="committed",
						)
						if git_result.push_attempted and git_result.push_succeeded:
							self.repository.update_ci_state(job_id, ci_status="committed")
						elif git_result.push_attempted:
							self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="push_failed")
						else:
							self.repository.update_ci_state(job_id, ci_status="not_triggered", ci_conclusion="push_disabled")
					else:
						self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="commit_failed")
				else:
					self.repository.update_ci_state(job_id, ci_status=final_ci_status, ci_conclusion=final_ci_conclusion)
			except Exception:
				logger.exception("deferred_post_processing_failed", extra={"job_id": str(job_id), "step": "post_process_deferred"})
				try:
					self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="deferred_error")
				except Exception:
					pass

		thread = threading.Thread(target=_run, daemon=True, name=f"post-process-{job_id}")
		thread.start()

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

		regenerated_request = GenerationRequest(
			session_id=session_id,
			input_mode=original["input_mode"],
			code_content=raw_code,
			filename=original.get("original_filename"),
			language=original["detected_language"],
			user_prompt=user_prompt + f" (rerun requested; preferred framework: {target_framework})",
		)
		response = self.generate(regenerated_request, [], idempotency_key=None)

		return RerunResult(
			original_job_id=job_id,
			rerun_job_id=response.job_id,
			status=JobStatus.completed,
			quality_score=response.quality_score,
			ci_status=response.ci_status,
			commit_sha=response.commit_sha,
		)

	def get_status(self, job_id: UUID, session_id: str) -> JobStatusView:
		job = self.repository.get_job(job_id, session_id=session_id)
		if not job:
			raise AppError("Job not found", status_code=404)
		return JobStatusView(
			job_id=job.id,
			status=job.status,
			ci_status=job.ci_status,
			ci_conclusion=job.ci_conclusion,
			ci_run_url=job.ci_run_url,
			ci_run_id=job.ci_run_id,
			ci_updated_at=job.ci_updated_at,
		)


def _build_metadata_payload(
	*,
	job_id: UUID,
	request: GenerationRequest,
	context: UnifiedContext,
	quality_score: int,
	framework_used: str,
	uncovered_areas: list[str],
) -> dict[str, Any]:
	return {
		"job_id": str(job_id),
		"session_id": request.session_id,
		"generation_timestamp": datetime.now(timezone.utc).isoformat(),
		"input_mode": request.input_mode.value,
		"quality_score": quality_score,
		"framework_used": framework_used,
		"uncovered_areas": uncovered_areas,
		"detected_language": context.detected_language.value,
		"source_filename": request.filename,
	}


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
