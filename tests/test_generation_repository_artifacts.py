from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.repositories.generation_repository import GenerationRepository
from backend.schemas import FeedbackValue, JobFeedbackRequest, Language


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
        if "SELECT detected_language" in query and "FROM generation_jobs" in query:
            return {
                "detected_language": "python",
                "user_prompt": "Generate",
                "generated_test_code": "def test_ok(): pass",
                "quality_score": 8,
                "framework_used": "pytest",
                "classified_intent": {"test_type": "unit"},
            }
        if "INSERT INTO generation_job_feedback" in query:
            return {
                "id": uuid4(),
                "job_id": params[1],
                "session_id": params[2],
                "feedback_value": params[3],
                "correction_text": params[4],
                "reviewer_notes": params[5],
                "detected_language": params[6],
                "user_prompt_snapshot": params[7],
                "generated_test_code_snapshot": params[8],
                "quality_score_snapshot": params[9],
                "framework_used_snapshot": params[10],
                "source_code_snapshot": params[11],
                "classified_intent_snapshot": {"test_type": "unit"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
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
                "output_test_path": "sessions/s1/python/add/test_add.py",
                "output_metadata_path": "sessions/s1/python/add/test_add.json",
            }
        if "FROM test_run_results" in query:
            return None
        return None

    def fetchall(self, query: str, params=()):
        self.last_query = query
        self.last_params = params
        if "FROM generation_job_feedback" in query:
            return [
                {
                    "job_id": uuid4(),
                    "detected_language": "python",
                    "framework_used_snapshot": "pytest",
                    "generated_test_code_snapshot": "def test_x(): pass",
                    "correction_text": None,
                    "reviewer_notes": "Solid coverage",
                    "quality_score_snapshot": 9,
                    "created_at": datetime.now(timezone.utc),
                }
            ]
        return []


def test_update_file_outputs_persists_paths() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)
    job_id = uuid4()

    repo.update_file_outputs(
        job_id=job_id,
        source_file_path="uploads/session-test-1/python/source.py",
        output_test_path="sessions/s1/python/add/test_add.py",
        output_metadata_path="sessions/s1/python/add/test_add.json",
    )

    assert "output_test_path" in db.last_query
    assert db.last_params[0] == "uploads/session-test-1/python/source.py"
    assert db.last_params[1] == "sessions/s1/python/add/test_add.py"
    assert db.last_params[2] == "sessions/s1/python/add/test_add.json"


def test_get_job_maps_artifact_path_fields() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)

    job = repo.get_job(uuid4(), session_id="session-test-1")

    assert job is not None
    assert job.source_file_path == "uploads/session-test-1/python/source.py"
    assert job.output_test_path == "sessions/s1/python/add/test_add.py"
    assert job.output_metadata_path == "sessions/s1/python/add/test_add.json"


def test_upsert_job_feedback_stores_snapshot_context() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)
    job_id = uuid4()

    feedback = repo.upsert_job_feedback(
        job_id=job_id,
        session_id="session-test-1",
        payload=JobFeedbackRequest(
            feedback_value=FeedbackValue.up,
            correction_text="Add exception path",
            reviewer_notes="Great baseline assertions",
        ),
    )

    assert "INSERT INTO generation_job_feedback" in db.last_query
    assert feedback.job_id == job_id
    assert feedback.feedback_value == FeedbackValue.up
    assert feedback.framework_used_snapshot == "pytest"


def test_recent_positive_feedback_examples_filters_by_language_and_framework() -> None:
    db = FakeDb()
    repo = GenerationRepository(db)

    examples = repo.get_recent_positive_feedback_examples(
        session_id="session-test-1",
        language=Language.python,
        framework_used="pytest",
        limit=3,
    )

    assert len(examples) == 1
    assert examples[0].detected_language == Language.python
    assert examples[0].framework_used_snapshot == "pytest"
