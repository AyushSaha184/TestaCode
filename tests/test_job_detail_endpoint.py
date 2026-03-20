from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import app
from backend.bootstrap import get_repository, get_storage_service
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
            source_file_url=None,
            output_test_path="sessions/session-test-1/python/add/test_add.py",
            output_metadata_path="sessions/session-test-1/python/add/test_add.json",
            output_test_url=None,
            output_metadata_url=None,
            auto_commit_enabled=False,
            commit_sha=None,
            workflow_name=None,
            ci_status="file_written",
            ci_conclusion=None,
            ci_run_url=None,
            ci_run_id=None,
            ci_updated_at=datetime.now(timezone.utc),
            latest_run=None,
        )


class FakeStorageService:
    def is_configured(self) -> bool:
        return True

    def resolve_object_url(self, object_path: str):
        return f"https://signed.local/{object_path}?token=1"


class FailingStorageService:
    def is_configured(self) -> bool:
        return True

    def resolve_object_url(self, object_path: str):
        raise RuntimeError("supabase unavailable")


def test_job_detail_includes_storage_urls() -> None:
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService()
    client = TestClient(app)
    job_id = str(uuid4())

    response = client.get(f"/jobs/{job_id}", headers={"X-Session-Id": "session-test-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["output_test_path"] == "sessions/session-test-1/python/add/test_add.py"
    assert payload["source_file_url"].startswith("https://signed.local/uploads/session-test-1/python/add.py")
    assert payload["output_test_url"].startswith("https://signed.local/sessions/session-test-1/python/add/test_add.py")
    assert payload["output_metadata_url"].startswith("https://signed.local/sessions/session-test-1/python/add/test_add.json")

    app.dependency_overrides.clear()


def test_job_detail_handles_storage_resolution_failure() -> None:
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_storage_service] = lambda: FailingStorageService()
    client = TestClient(app)
    job_id = str(uuid4())

    response = client.get(f"/jobs/{job_id}", headers={"X-Session-Id": "session-test-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["output_test_url"] is None
    assert payload["output_metadata_url"] is None
    assert "Artifact URL refresh is temporarily unavailable" in payload["warnings"]

    app.dependency_overrides.clear()
