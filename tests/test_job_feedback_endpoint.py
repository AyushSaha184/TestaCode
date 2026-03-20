from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.app import app
from backend.bootstrap import get_repository
from backend.schemas import FeedbackValue, JobFeedbackRequest, JobFeedbackResponse, Language


class FakeRepository:
    def __init__(self) -> None:
        self.jobs_by_session: dict[tuple[str, str], dict] = {}
        self.feedback_by_key: dict[tuple[str, str], JobFeedbackResponse] = {}

    def add_job(self, job_id: UUID, session_id: str) -> None:
        self.jobs_by_session[(str(job_id), session_id)] = {"id": job_id}

    def get_job_record(self, job_id, session_id):
        return self.jobs_by_session.get((str(job_id), session_id))

    def upsert_job_feedback(self, job_id: UUID, session_id: str, payload: JobFeedbackRequest) -> JobFeedbackResponse:
        now = datetime.now(timezone.utc)
        key = (str(job_id), session_id)
        existing = self.feedback_by_key.get(key)
        feedback = JobFeedbackResponse(
            id=existing.id if existing else uuid4(),
            job_id=job_id,
            session_id=session_id,
            feedback_value=payload.feedback_value,
            correction_text=payload.correction_text,
            reviewer_notes=payload.reviewer_notes,
            detected_language=Language.python,
            user_prompt_snapshot="Generate tests",
            generated_test_code_snapshot="def test_ok():\n    assert True",
            quality_score_snapshot=8,
            framework_used_snapshot="pytest",
            source_code_snapshot=None,
            classified_intent_snapshot={"test_type": "unit"},
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self.feedback_by_key[key] = feedback
        return feedback

    def get_job_feedback(self, job_id: UUID, session_id: str) -> JobFeedbackResponse | None:
        return self.feedback_by_key.get((str(job_id), session_id))


def test_job_feedback_submit_and_fetch() -> None:
    repo = FakeRepository()
    job_id = uuid4()
    repo.add_job(job_id, "session-test-1")

    app.dependency_overrides[get_repository] = lambda: repo
    client = TestClient(app)

    submit_response = client.post(
        f"/jobs/{job_id}/feedback",
        headers={"X-Session-Id": "session-test-1"},
        json={
            "feedback_value": "up",
            "correction_text": "Please add parameterized edge cases",
            "reviewer_notes": "Strong baseline assertions",
        },
    )

    assert submit_response.status_code == 200
    submit_payload = submit_response.json()
    assert submit_payload["job_id"] == str(job_id)
    assert submit_payload["feedback_value"] == "up"
    assert submit_payload["correction_text"] == "Please add parameterized edge cases"

    fetch_response = client.get(f"/jobs/{job_id}/feedback", headers={"X-Session-Id": "session-test-1"})
    assert fetch_response.status_code == 200
    fetch_payload = fetch_response.json()
    assert fetch_payload["feedback_value"] == "up"
    assert fetch_payload["reviewer_notes"] == "Strong baseline assertions"

    # Upsert behavior updates the single per-job-per-session record.
    update_response = client.post(
        f"/jobs/{job_id}/feedback",
        headers={"X-Session-Id": "session-test-1"},
        json={"feedback_value": FeedbackValue.down.value, "reviewer_notes": "Misses negative path"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["feedback_value"] == "down"

    app.dependency_overrides.clear()


def test_job_feedback_isolation_and_not_found() -> None:
    repo = FakeRepository()
    job_id = uuid4()
    repo.add_job(job_id, "session-owner")

    app.dependency_overrides[get_repository] = lambda: repo
    client = TestClient(app)

    outsider_get = client.get(f"/jobs/{job_id}/feedback", headers={"X-Session-Id": "session-other"})
    assert outsider_get.status_code == 404

    outsider_post = client.post(
        f"/jobs/{job_id}/feedback",
        headers={"X-Session-Id": "session-other"},
        json={"feedback_value": "up"},
    )
    assert outsider_post.status_code == 404

    missing_job_id = uuid4()
    missing_job = client.get(f"/jobs/{missing_job_id}/feedback", headers={"X-Session-Id": "session-owner"})
    assert missing_job.status_code == 404

    app.dependency_overrides.clear()


def test_job_feedback_validation_contract() -> None:
    repo = FakeRepository()
    job_id = uuid4()
    repo.add_job(job_id, "session-test-1")

    app.dependency_overrides[get_repository] = lambda: repo
    client = TestClient(app)

    invalid_response = client.post(
        f"/jobs/{job_id}/feedback",
        headers={"X-Session-Id": "session-test-1"},
        json={"feedback_value": "invalid"},
    )

    assert invalid_response.status_code == 422

    app.dependency_overrides.clear()
