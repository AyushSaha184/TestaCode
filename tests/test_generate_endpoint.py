from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import app
from backend.bootstrap import get_orchestrator
from backend.schemas import GenerationRequest, GenerationResponse, JobStatus, JobStatusView, Language, RerunResult


class FakeOrchestrator:
    def generate(self, request: GenerationRequest, initial_warnings: list[str], idempotency_key: str | None) -> GenerationResponse:
        assert request.user_prompt
        assert request.session_id
        return GenerationResponse(
            job_id=uuid4(),
            detected_language=Language.python,
            generated_test_code="def test_ok():\n    assert True",
            quality_score=8,
            uncovered_areas=["null input"],
            warnings=initial_warnings,
            framework_used="pytest",
            source_file_path="uploads/session-test-1/python/add.py",
            source_file_url="https://storage.local/add.py",
            output_test_path="generated_tests/python/add/test_add.py",
            output_metadata_path="generated_tests/python/add/test_add.json",
            output_test_url="https://storage.local/test_add.py",
            output_metadata_url="https://storage.local/test_add.json",
            commit_sha="abc123",
            ci_status="ci_pending",
        )

    def rerun(self, job_id, session_id):
        assert session_id
        return RerunResult(
            original_job_id=job_id,
            rerun_job_id=uuid4(),
            status=JobStatus.completed,
            quality_score=8,
            ci_status="not_triggered",
            commit_sha="abc123",
        )

    def get_status(self, job_id, session_id):
        assert session_id
        return JobStatusView(
            job_id=job_id,
            status=JobStatus.completed,
            ci_status="file_written",
            ci_conclusion=None,
            ci_run_url=None,
            ci_run_id=None,
            ci_updated_at=None,
        )


def test_generate_endpoint_form_contract() -> None:
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "input_mode": "paste",
            "user_prompt": "Create unit tests",
            "code_content": "def add(a, b): return a + b",
            "language": "python",
        },
        headers={"Idempotency-Key": "abc-123", "X-Session-Id": "session-test-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["framework_used"] == "pytest"
    assert payload["quality_score"] == 8
    assert payload["detected_language"] == "python"
    assert payload["source_file_path"] == "uploads/session-test-1/python/add.py"
    assert payload["source_file_url"] == "https://storage.local/add.py"
    assert payload["output_test_path"] == "generated_tests/python/add/test_add.py"
    assert payload["output_test_url"] == "https://storage.local/test_add.py"
    assert payload["commit_sha"] == "abc123"

    app.dependency_overrides.clear()


def test_status_endpoints_contract() -> None:
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)
    job_id = str(uuid4())

    status_response = client.get(f"/jobs/{job_id}/status", headers={"X-Session-Id": "session-test-1"})
    assert status_response.status_code == 200
    assert status_response.json()["ci_status"] == "file_written"

    app.dependency_overrides.clear()
