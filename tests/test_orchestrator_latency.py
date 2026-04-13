from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from backend.agents.orchestrator import GenerationOrchestrator
from backend.schemas import (
    FeedbackValue,
    FunctionMetadata,
    GenerationRequest,
    GenerationResponse,
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
        self.completed_analysis_text: str | None = None
        self.file_outputs_updates: list[dict[str, object]] = []

    def get_job(self, job_id: UUID, session_id: str):
        return None

    def create_job(
        self,
        payload: GenerationRequest,
        status: JobStatus = JobStatus.queued,
        idempotency_key: str | None = None,
    ) -> UUID:
        return uuid4()

    def update_job_processing(self, job_id: UUID) -> None:
        return None

    def update_job_completed(
        self,
        job_id: UUID,
        classified_intent,
        analysis_text: str,
        generated_test_code: str,
        quality_score: int,
        framework_used: str,
        warnings: list[str],
        uncovered_areas: list[str],
    ) -> None:
        self.completed_analysis_text = analysis_text

    def append_warning(self, job_id: UUID, warning: str) -> None:
        return None

    def update_file_outputs(
        self, job_id: UUID, source_file_path, output_test_path, output_metadata_path
    ) -> None:
        self.file_outputs_updates.append(
            {
                "output_test_path": output_test_path,
                "output_metadata_path": output_metadata_path,
            }
        )

    def record_test_run(
        self,
        job_id: UUID,
        pass_count: int,
        fail_count: int,
        error_count: int,
        coverage_percentage: float,
        raw_results: dict[str, object] | None = None,
    ) -> None:
        return None

    def get_job_feedback(self, job_id: UUID, session_id: str):
        return None

    def update_job_failed(self, job_id: UUID, warnings: list[str]) -> None:
        raise AssertionError("generate() should not fail in this test")


class FakeInputService:
    def build_unified_context(
        self, request: GenerationRequest, base_warnings: list[str]
    ) -> UnifiedContext:
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

    def run_validation_and_correction(
        self, context: UnifiedContext, generated_code: str
    ) -> tuple[str, list[str]]:
        return generated_code, []

    def run_self_evaluation(
        self, context: UnifiedContext, generated_code: str
    ) -> tuple[int, list[str]]:
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


def test_generate_persists_analysis_and_file_outputs(monkeypatch) -> None:
    repository = FakeRepository()
    orchestrator = GenerationOrchestrator(
        repository=repository,
        input_service=FakeInputService(),
        chain=FakeChain(),
        file_output_service=FakeFileOutputService(),
    )

    response = orchestrator.generate(
        GenerationRequest(
            session_id="session-test",
            input_mode=InputMode.upload,
            code_content="def add(a, b): return a + b",
            filename="add.py",
            language=Language.python,
            user_prompt="Generate unit tests",
        ),
        initial_warnings=[],
        idempotency_key=None,
    )

    assert response.quality_score == 7
    assert repository.completed_analysis_text is not None
    assert "Intent:" in repository.completed_analysis_text
    assert repository.file_outputs_updates[-1]["output_test_path"] is not None


def test_rerun_rehydrates_enum_fields(monkeypatch) -> None:
    repository = FakeRepository()
    orchestrator = GenerationOrchestrator(
        repository=repository,
        input_service=FakeInputService(),
        chain=FakeChain(),
        file_output_service=FakeFileOutputService(),
    )
    source_job_id = uuid4()

    def _fake_get_job_record(job_id: UUID, session_id: str):
        assert job_id == source_job_id
        assert session_id == "session-test"
        return {
            "input_mode": "paste",
            "detected_language": "python",
            "classified_intent": {
                "raw_code": "def add(a, b): return a + b",
                "intent": {"target_framework": "pytest"},
            },
            "user_prompt": "Generate tests",
            "original_filename": "add.py",
        }

    repository.get_job_record = _fake_get_job_record  # type: ignore[attr-defined]

    captured_request: dict[str, object] = {}

    def _fake_generate(
        request: GenerationRequest,
        initial_warnings: list[str],
        idempotency_key: str | None,
    ):
        captured_request["request"] = request
        return GenerationResponse(
            job_id=uuid4(),
            detected_language=Language.python,
            generated_test_code="def test_ok():\n    assert True",
            quality_score=8,
            framework_used="pytest",
        )

    monkeypatch.setattr(orchestrator, "generate", _fake_generate)

    orchestrator.rerun(source_job_id, session_id="session-test")

    request = captured_request["request"]
    assert isinstance(request, GenerationRequest)
    assert request.input_mode == InputMode.paste
    assert request.language == Language.python


def test_rerun_preserves_original_prompt_even_with_feedback(monkeypatch) -> None:
    repository = FakeRepository()
    orchestrator = GenerationOrchestrator(
        repository=repository,
        input_service=FakeInputService(),
        chain=FakeChain(),
        file_output_service=FakeFileOutputService(),
    )
    source_job_id = uuid4()

    def _fake_get_job_record(job_id: UUID, session_id: str):
        assert job_id == source_job_id
        assert session_id == "session-test"
        return {
            "input_mode": "paste",
            "detected_language": "python",
            "classified_intent": {
                "raw_code": "def add(a, b): return a + b",
                "intent": {"target_framework": "pytest"},
            },
            "user_prompt": "Generate tests",
            "original_filename": "add.py",
            "generated_test_code": "def test_old():\n    assert add(1, 2) == 3\n",
        }

    repository.get_job_record = _fake_get_job_record  # type: ignore[attr-defined]
    repository.get_job_feedback = lambda job_id, session_id: SimpleNamespace(  # type: ignore[attr-defined]
        feedback_value=FeedbackValue.down,
        correction_text="Use parametrized tests and add edge cases",
        reviewer_notes=None,
    )

    captured_request: dict[str, object] = {}

    def _fake_generate(
        request: GenerationRequest,
        initial_warnings: list[str],
        idempotency_key: str | None,
    ):
        captured_request["request"] = request
        return GenerationResponse(
            job_id=uuid4(),
            detected_language=Language.python,
            generated_test_code="def test_ok():\n    assert True",
            quality_score=8,
            framework_used="pytest",
        )

    monkeypatch.setattr(orchestrator, "generate", _fake_generate)

    orchestrator.rerun(source_job_id, session_id="session-test")

    request = captured_request["request"]
    assert isinstance(request, GenerationRequest)
    assert request.user_prompt == "Generate tests"
