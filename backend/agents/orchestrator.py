from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.agents.chains import TestGenerationChain
from backend.core.cache import CacheBackend, TTLCache
from backend.core.exceptions import AppError
from backend.core.logger import get_logger
from backend.input.handlers import InputProcessingService
from backend.repositories.generation_repository import GenerationRepository
from backend.services.ci_integration_service import CIState, GitHubCIIntegrationService
from backend.services.file_output_service import FileOutputResult, FileOutputService
from backend.services.git_integration_service import GitIntegrationService
from backend.schemas import (
	GenerationRequest,
	GenerationResponse,
	JobStatusView,
	JobStatus,
	RerunResult,
)

logger = get_logger(__name__)


class GenerationOrchestrator:
	def __init__(
		self,
		repository: GenerationRepository,
		input_service: InputProcessingService,
		chain: TestGenerationChain,
		file_output_service: FileOutputService,
		git_integration_service: GitIntegrationService,
		ci_integration_service: GitHubCIIntegrationService | None,
		workflow_name: str,
		idempotency_ttl_seconds: int,
		idempotency_cache: CacheBackend[str, UUID] | None = None,
	) -> None:
		self.repository = repository
		self.input_service = input_service
		self.chain = chain
		self.file_output_service = file_output_service
		self.git_integration_service = git_integration_service
		self.ci_integration_service = ci_integration_service
		self.workflow_name = workflow_name
		self.idempotency_cache = idempotency_cache or TTLCache[str, UUID](idempotency_ttl_seconds)

	def generate(self, request: GenerationRequest, initial_warnings: list[str], idempotency_key: str | None) -> GenerationResponse:
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
		source_file_path: str | None = None
		source_file_url: str | None = None
		output_test_url: str | None = None
		output_metadata_url: str | None = None

		try:
			self.repository.update_job_processing(job_id)
			if request.input_mode.value == "upload" and request.filename:
				try:
					source_file_path, source_file_url = self.file_output_service.upload_source_file(
						session_id=request.session_id,
						original_filename=request.filename,
						detected_language=request.language,
						source_code=request.code_content,
					)
				except Exception as source_exc:
					warning = f"Source file upload failed: {source_exc}"
					warnings.append(warning)
					self.repository.append_warning(job_id, warning)

			context = self.input_service.build_unified_context(request, warnings)
			analysis_text = self.chain.run_analysis(context)
			generated_code = self.chain.run_generation(context, analysis_text)
			generated_code, validation_warnings = self.chain.run_validation_and_correction(context, generated_code)
			warnings.extend(validation_warnings)

			quality_score, uncovered_areas = self.chain.run_self_evaluation(context, generated_code)
			framework_used = _resolve_framework(context.classified_intent.target_framework.value, request.language.value)

			mock_warnings = _derive_mocking_warnings(context)
			warnings.extend(mock_warnings)

			classified_intent_payload: dict[str, Any] = {
				"intent": context.classified_intent.model_dump(mode="json"),
				"raw_code": context.raw_code,
				"function_metadata": [item.model_dump(mode="json") for item in context.function_metadata],
			}

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

				output_test_url = file_result.test_file_url
				output_metadata_url = file_result.metadata_file_url
				artifact_status = "file_written" if file_result.test_file_path and file_result.metadata_file_path else "artifact_partial"
				self.repository.update_file_outputs(
					job_id,
					source_file_path=source_file_path,
					source_file_url=source_file_url,
					output_test_path=file_result.test_file_path,
					output_metadata_path=file_result.metadata_file_path,
					output_test_url=file_result.test_file_url,
					output_metadata_url=file_result.metadata_file_url,
					ci_status=artifact_status,
				)
				ci_status = artifact_status
				if artifact_status == "artifact_partial":
					ci_conclusion = "storage_upload_partial"
			except Exception as file_exc:
				warning = f"File output failed: {file_exc}"
				warnings.append(warning)
				self.repository.append_warning(job_id, warning)
				self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="file_write_failed")
				ci_status = "ci_unavailable"
				ci_conclusion = "file_write_failed"

			if request.auto_commit_enabled and file_result is not None and file_result.local_test_file_path and file_result.local_metadata_file_path:
				git_result = self.git_integration_service.commit_generated_outputs(
					job_id=job_id,
					feature_name=file_result.feature_name,
					test_file_path=file_result.local_test_file_path,
					metadata_file_path=file_result.local_metadata_file_path,
				)
				if git_result.warning:
					warnings.append(git_result.warning)
					self.repository.append_warning(job_id, git_result.warning)

				if git_result.committed:
					commit_sha = git_result.commit_sha
					self.repository.update_commit_state(
						job_id,
						commit_sha=git_result.commit_sha,
						ci_status="committed",
						workflow_name=self.workflow_name,
					)
					if git_result.push_attempted and git_result.push_succeeded:
						ci_status = "ci_pending"
						self.repository.update_ci_state(job_id, ci_status="ci_pending", workflow_name=self.workflow_name)
					elif git_result.push_attempted and not git_result.push_succeeded:
						ci_status = "ci_unavailable"
						ci_conclusion = "push_failed"
						self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="push_failed")
					else:
						ci_status = "not_triggered"
						self.repository.update_ci_state(job_id, ci_status="not_triggered", ci_conclusion="push_disabled")
				else:
					ci_status = "ci_unavailable"
					ci_conclusion = "commit_failed"
					self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="commit_failed")
			else:
				if request.auto_commit_enabled and file_result is None:
					ci_status = "ci_unavailable"
					self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="commit_skipped")
				else:
					preserved_statuses = {"file_written", "artifact_partial", "ci_unavailable"}
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

			return GenerationResponse(
				job_id=job_id,
				generated_test_code=generated_code,
				quality_score=quality_score,
				uncovered_areas=uncovered_areas,
				warnings=warnings,
				framework_used=framework_used,
				source_file_path=source_file_path,
				source_file_url=source_file_url,
				output_test_path=file_result.test_file_path if file_result else None,
				output_metadata_path=file_result.metadata_file_path if file_result else None,
				output_test_url=output_test_url,
				output_metadata_url=output_metadata_url,
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

	def poll_ci(self, job_id: UUID, session_id: str) -> JobStatusView:
		if self.ci_integration_service is None:
			self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="ci_disabled")
		else:
			try:
				state: CIState = self.ci_integration_service.poll_by_job_id(job_id, session_id=session_id)
				if state.ci_status:
					self.repository.update_ci_state(
						job_id,
						ci_status=state.ci_status,
						ci_conclusion=state.ci_conclusion,
						ci_run_url=state.ci_run_url,
						ci_run_id=state.ci_run_id,
						workflow_name=self.workflow_name,
					)
			except Exception as exc:
				warning = f"CI polling failed: {exc}"
				self.repository.append_warning(job_id, warning)
				self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="poll_failed")

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


def _resolve_framework(requested: str, language: str) -> str:
	if requested != "unspecified":
		return requested
	if language == "python":
		return "pytest"
	if language in ("javascript", "typescript"):
		return "jest"
	if language == "java":
		return "junit"
	return "unspecified"


def _derive_mocking_warnings(context) -> list[str]:
	hints = sorted({hint for fn in context.function_metadata for hint in fn.dependency_hints})
	if not hints:
		return []
	joined = ", ".join(hints[:8])
	if context.detected_language.value == "python":
		return [f"Detected dependency candidates for patch/MagicMock: {joined}"]
	if context.detected_language.value in ("javascript", "typescript"):
		return [f"Detected dependency candidates for jest.mock: {joined}"]
	return [f"Detected dependency candidates: {joined}"]
