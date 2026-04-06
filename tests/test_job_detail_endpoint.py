from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import app
from backend.bootstrap import get_repository
from backend.schemas import InputMode, JobDetail, JobStatus, Language


class FakeRepository:
    def get_job(self, job_id, session_id):
        assert session_id == "session-test-1"
        return JobDetail(
            id=job_id,
            created_at=datetime.now(timezone.utc),
            input_mode=InputMode.paste,
            original_filename=None,
            detected_language=Language.python,
            user_prompt="Generate tests",
            classified_intent={},
            analysis_text="ok",
            generated_test_code="def test_ok(): pass",
            quality_score=8,
            status=JobStatus.completed,
            framework_used="pytest",
            warnings=[],
            uncovered_areas=[],
            source_file_path="uploads/session-test-1/python/add.py",
            output_test_path="sessions/session-test-1/python/add/test_add.py",
            output_metadata_path="sessions/session-test-1/python/add/test_add.json",
            latest_run=None,
        )


def test_job_detail_returns_basic_fields() -> None:
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    client = TestClient(app)
    job_id = str(uuid4())

    response = client.get(f"/jobs/{job_id}", headers={"X-Session-Id": "session-test-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["output_test_path"] == "sessions/session-test-1/python/add/test_add.py"
    assert payload["status"] == "completed"
    assert payload["framework_used"] == "pytest"

    app.dependency_overrides.clear()
