from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.repositories.generation_repository import GenerationRepository


class FakeDb:
    def __init__(self) -> None:
        self.last_query = ""
        self.last_params = ()

    def execute(self, query: str, params=()):
        self.last_query = query
        self.last_params = params

    def fetchone(self, query: str, params=()):
        self.last_query = query
        self.last_params = params
        if "FROM generation_jobs" in query:
            return {
                "id": uuid4(),
                "created_at": datetime.now(timezone.utc),
                "input_mode": "paste",
                "original_filename": None,
                "detected_language": "python",
                "user_prompt": "Generate",
                "classified_intent": {},
                "analysis_text": None,
                "generated_test_code": "def test_ok(): pass",
                "quality_score": 8,
                "status": "completed",
                "framework_used": "pytest",
                "warnings": [],
                "uncovered_areas": [],
                "source_file_path": "uploads/session-test-1/python/source.py",
                "source_file_url": "https://storage.local/source.py",
                "output_test_path": "sessions/s1/python/add/test_add.py",
                "output_metadata_path": "sessions/s1/python/add/test_add.json",
                "output_test_url": "https://storage.local/test_add.py",
                "output_metadata_url": "https://storage.local/test_add.json",
                "auto_commit_enabled": False,
                "commit_sha": None,
                "workflow_name": None,
                "ci_status": "file_written",
                "ci_conclusion": None,
                "ci_run_url": None,
                "ci_run_id": None,
                "ci_updated_at": datetime.now(timezone.utc),
            }
        if "FROM test_run_results" in query:
            return None
        return None

    def fetchall(self, query: str, params=()):
        self.last_query = query
        self.last_params = params
        return []


def test_update_file_outputs_persists_paths_and_urls() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)
    job_id = uuid4()

    repo.update_file_outputs(
        job_id=job_id,
        source_file_path="uploads/session-test-1/python/source.py",
        source_file_url="https://storage.local/source.py",
        output_test_path="sessions/s1/python/add/test_add.py",
        output_metadata_path="sessions/s1/python/add/test_add.json",
        output_test_url="https://storage.local/test_add.py",
        output_metadata_url="https://storage.local/test_add.json",
        ci_status="file_written",
    )

    assert "output_test_url" in db.last_query
    assert db.last_params[0] == "uploads/session-test-1/python/source.py"
    assert db.last_params[1] == "https://storage.local/source.py"
    assert db.last_params[2] == "sessions/s1/python/add/test_add.py"
    assert db.last_params[4] == "https://storage.local/test_add.py"
    assert db.last_params[6] == "file_written"


def test_get_job_maps_artifact_url_fields() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)

    job = repo.get_job(uuid4(), session_id="session-test-1")

    assert job is not None
    assert job.source_file_path == "uploads/session-test-1/python/source.py"
    assert job.source_file_url == "https://storage.local/source.py"
    assert job.output_test_path == "sessions/s1/python/add/test_add.py"
    assert job.output_metadata_path == "sessions/s1/python/add/test_add.json"
    assert job.output_test_url == "https://storage.local/test_add.py"
    assert job.output_metadata_url == "https://storage.local/test_add.json"
