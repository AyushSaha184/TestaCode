from __future__ import annotations

from uuid import UUID, uuid4

from backend.agents.orchestrator import GenerationOrchestrator
from backend.schemas import (
	FunctionMetadata,
	GenerationRequest,
	InputMode,
	IntentClassification,
	JobStatus,
	Language,
	TargetFramework,
	TestType,
	UnifiedContext,
)


class FakeRepository:
	def __init__(self) -> None:
		self.updated_ci_states: list[str] = []
		self.completed_analysis_text: str | None = None
		self.file_outputs_updates: list[dict[str, object]] = []

	def get_job(self, job_id: UUID, session_id: str):
		return None

	def create_job(self, payload: GenerationRequest, status: JobStatus = JobStatus.queued) -> UUID:
		return uuid4()

	def update_job_processing(self, job_id: UUID) -> None:
		return None

	def update_job_completed(self, job_id: UUID, classified_intent, analysis_text: str, generated_test_code: str, quality_score: int, framework_used: str, warnings: list[str], uncovered_areas: list[str]) -> None:
		self.completed_analysis_text = analysis_text

	def append_warning(self, job_id: UUID, warning: str) -> None:
		return None

	def update_file_outputs(self, job_id: UUID, source_file_path, source_file_url, output_test_path, output_metadata_path, output_test_url, output_metadata_url, ci_status: str) -> None:
		self.file_outputs_updates.append(
			{
				"output_test_path": output_test_path,
				"output_metadata_path": output_metadata_path,
				"ci_status": ci_status,
			}
		)

	def update_ci_state(self, job_id: UUID | str, *, ci_status: str, ci_conclusion: str | None = None, ci_run_url: str | None = None, ci_run_id: str | None = None, workflow_name: str | None = None) -> None:
		self.updated_ci_states.append(ci_status)

	def record_test_run(self, job_id: UUID, pass_count: int, fail_count: int, error_count: int, coverage_percentage: float, raw_results: dict[str, object] | None = None) -> None:
		return None

	def update_job_failed(self, job_id: UUID, warnings: list[str]) -> None:
		raise AssertionError("generate() should not fail in this test")


class FakeInputService:
	def build_unified_context(self, request: GenerationRequest, base_warnings: list[str]) -> UnifiedContext:
		return UnifiedContext(
			raw_code="def add(a, b):\n    return a + b\n",
			detected_language=Language.python,
			function_metadata=[FunctionMetadata(name="add")],
			classified_intent=IntentClassification(
				test_type=TestType.unit,
				target_scope="add",
				target_framework=TargetFramework.pytest,
				special_requirements=[],
				confidence=0.9,
			),
			original_prompt=request.user_prompt,
			warnings=base_warnings,
		)


class FakeChain:
	def run_generation(self, context: UnifiedContext) -> str:
		return "def test_add():\n    assert add(1, 2) == 3\n"

	def run_validation_and_correction(self, context: UnifiedContext, generated_code: str) -> tuple[str, list[str]]:
		return generated_code, []

	def run_self_evaluation(self, context: UnifiedContext, generated_code: str) -> tuple[int, list[str]]:
		return 7, []


class FakeFileOutputService:
	def write_outputs(self, **kwargs):
		from backend.services.file_output_service import FileOutputResult

		return FileOutputResult(
			feature_name="add",
			local_test_file_path="generated_tests/session-test/python/add/test_add.py",
			local_metadata_file_path="generated_tests/session-test/python/add/test_add.json",
			warnings=[],
		)

	def is_storage_configured(self) -> bool:
		return True


class FakeGitService:
	def commit_generated_outputs(self, **kwargs):
		raise AssertionError("git should be deferred, not run inline")


def test_generate_persists_deferred_status_and_analysis_summary(monkeypatch) -> None:
	repository = FakeRepository()
	orchestrator = GenerationOrchestrator(
		repository=repository,
		input_service=FakeInputService(),
		chain=FakeChain(),
		file_output_service=FakeFileOutputService(),
		git_integration_service=FakeGitService(),
		idempotency_ttl_seconds=60,
	)
	deferred_calls: list[dict[str, object]] = []

	def _capture_deferred(**kwargs) -> None:
		deferred_calls.append(kwargs)

	monkeypatch.setattr(orchestrator, "_defer_post_processing", _capture_deferred)

	response = orchestrator.generate(
		GenerationRequest(
			session_id="session-test",
			input_mode=InputMode.upload,
			code_content="def add(a, b): return a + b",
			filename="add.py",
			language=Language.python,
			user_prompt="Generate unit tests",
			auto_commit_enabled=True,
		),
		initial_warnings=[],
		idempotency_key=None,
	)

	assert response.ci_status == "deferred"
	assert repository.updated_ci_states[-1] == "deferred"
	assert repository.completed_analysis_text is not None
	assert "Intent:" in repository.completed_analysis_text
	assert deferred_calls
