from __future__ import annotations

from uuid import uuid4

from backend.services.ci_integration_service import GitHubCIIntegrationService


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self, responses: list[dict]):
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def get(self, url, params=None):
        return FakeResponse(self._responses.pop(0))


class FakeRepository:
    def __init__(self, job_id):
        self.job_id = job_id
        self.states: list[str] = []

    def get_job_record(self, job_id, session_id):
        assert job_id == self.job_id
        assert session_id == "session-test-1"
        return {"id": job_id, "commit_sha": "abc123"}

    def update_ci_state(self, job_id, **kwargs):
        self.states.append(kwargs["ci_status"])


def test_ci_polling_transitions(monkeypatch) -> None:
    job_id = uuid4()
    repo = FakeRepository(job_id)

    responses = [
        {"workflow_runs": [{"status": "queued", "conclusion": None, "html_url": "http://run/1", "id": 1, "name": "generated-tests-ci"}]},
        {"workflow_runs": [{"status": "in_progress", "conclusion": None, "html_url": "http://run/1", "id": 1, "name": "generated-tests-ci"}]},
        {"workflow_runs": [{"status": "completed", "conclusion": "success", "html_url": "http://run/1", "id": 1, "name": "generated-tests-ci"}]},
    ]

    import backend.services.ci_integration_service as ci_module

    monkeypatch.setattr(ci_module.httpx, "Client", lambda timeout, headers: FakeClient(responses))
    monkeypatch.setattr(ci_module.time, "sleep", lambda *_: None)

    service = GitHubCIIntegrationService(
        token="token",
        owner="o",
        repo="r",
        workflow_name="generated-tests-ci",
        poll_interval_seconds=0,
        repository=repo,
    )

    state = service.poll_by_job_id(job_id, session_id="session-test-1")

    assert state.ci_status == "ci_passed"
    assert state.ci_conclusion == "success"
    assert repo.states[0] == "ci_pending"
    assert "ci_running" in repo.states
    assert repo.states[-1] == "ci_passed"
