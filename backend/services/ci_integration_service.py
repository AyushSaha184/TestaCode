from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import httpx

from backend.core.logger import get_logger
from backend.repositories.generation_repository import GenerationRepository

logger = get_logger(__name__)

TERMINAL_CONCLUSIONS = {"success", "failure", "cancelled", "timed_out"}


@dataclass(frozen=True)
class CIState:
    ci_status: str
    ci_conclusion: str | None
    ci_run_url: str | None
    ci_run_id: str | None


class GitHubCIIntegrationService:
    def __init__(
        self,
        *,
        token: str,
        owner: str,
        repo: str,
        workflow_name: str,
        poll_interval_seconds: int,
        repository: GenerationRepository,
    ) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.workflow_name = workflow_name
        self.poll_interval_seconds = poll_interval_seconds
        self.repository = repository

    def poll_by_job_id(self, job_id: UUID, session_id: str) -> CIState:
        job = self.repository.get_job_record(job_id, session_id=session_id)
        if not job:
            raise ValueError("Job not found")

        commit_sha = job.get("commit_sha")
        if not commit_sha:
            self.repository.update_ci_state(job_id, ci_status="ci_unavailable", ci_conclusion="missing_commit_sha")
            return CIState("ci_unavailable", "missing_commit_sha", None, None)

        logger.info("ci_poll_started", extra={"step": "ci", "job_id": str(job_id), "status": "processing"})

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        with httpx.Client(timeout=20.0, headers=headers) as client:
            while True:
                run = self._fetch_latest_run(client, commit_sha)
                if run is None:
                    self.repository.update_ci_state(job_id, ci_status="ci_pending", workflow_name=self.workflow_name)
                    logger.info("ci_poll_progress", extra={"step": "ci", "job_id": str(job_id), "status": "ci_pending"})
                    time.sleep(self.poll_interval_seconds)
                    continue

                status = run.get("status")
                conclusion = run.get("conclusion")
                html_url = run.get("html_url")
                run_id = run.get("id")

                if status == "completed":
                    ci_status = "ci_passed" if conclusion == "success" else "ci_failed"
                    self.repository.update_ci_state(
                        job_id,
                        ci_status=ci_status,
                        ci_conclusion=conclusion,
                        ci_run_url=html_url,
                        ci_run_id=str(run_id) if run_id is not None else None,
                        workflow_name=self.workflow_name,
                    )
                    logger.info("ci_poll_completed", extra={"step": "ci", "job_id": str(job_id), "status": ci_status})
                    return CIState(ci_status, conclusion, html_url, str(run_id) if run_id is not None else None)

                if status in {"queued", "requested", "waiting"}:
                    mapped_status = "ci_pending"
                else:
                    mapped_status = "ci_running"

                self.repository.update_ci_state(
                    job_id,
                    ci_status=mapped_status,
                    ci_conclusion=conclusion,
                    ci_run_url=html_url,
                    ci_run_id=str(run_id) if run_id is not None else None,
                    workflow_name=self.workflow_name,
                )
                logger.info("ci_poll_progress", extra={"step": "ci", "job_id": str(job_id), "status": mapped_status})
                time.sleep(self.poll_interval_seconds)

    def _fetch_latest_run(self, client: httpx.Client, commit_sha: str) -> dict | None:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/actions/runs"
        response = client.get(url, params={"head_sha": commit_sha, "per_page": 20})
        response.raise_for_status()
        payload = response.json()
        runs = payload.get("workflow_runs", [])

        for run in runs:
            workflow_name = run.get("name") or ""
            workflow_path = run.get("path") or ""
            if self.workflow_name and self.workflow_name not in workflow_name and self.workflow_name not in workflow_path:
                continue
            conclusion = run.get("conclusion")
            if conclusion in TERMINAL_CONCLUSIONS or run.get("status") in {"queued", "in_progress", "completed", "requested", "waiting"}:
                return run
        return runs[0] if runs else None
