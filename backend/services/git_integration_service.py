from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from backend.util.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GitCommitResult:
    committed: bool
    commit_sha: str | None
    push_attempted: bool
    push_succeeded: bool
    warning: str | None


class GitIntegrationService:
    def __init__(
        self,
        repository_root: str,
        generated_tests_dir: str,
        author_name: str,
        author_email: str,
        enable_git_push: bool,
    ) -> None:
        self.repository_root = Path(repository_root)
        self.generated_tests_root = (self.repository_root / generated_tests_dir).resolve()
        self.author_name = author_name
        self.author_email = author_email
        self.enable_git_push = enable_git_push

    def commit_generated_outputs(
        self,
        *,
        job_id: UUID,
        feature_name: str,
        test_file_path: str,
        metadata_file_path: str,
    ) -> GitCommitResult:
        logger.info("git_commit_started", extra={"step": "git", "job_id": str(job_id), "status": "processing"})

        test_path = self._validate_allowed_path(test_file_path)
        metadata_path = self._validate_allowed_path(metadata_file_path)

        rel_test = test_path.relative_to(self.repository_root).as_posix()
        rel_meta = metadata_path.relative_to(self.repository_root).as_posix()

        add_result = self._run_git(["add", rel_test, rel_meta])
        if add_result.returncode != 0:
            warning = f"git add failed: {add_result.stderr.strip() or add_result.stdout.strip()}"
            logger.warning("git_commit_failed", extra={"step": "git", "job_id": str(job_id), "status": "failed"})
            return GitCommitResult(False, None, False, False, warning)

        commit_message = f"testgen: add generated tests for {feature_name} (job {job_id})"
        commit_result = self._run_git(
            [
                "-c",
                f"user.name={self.author_name}",
                "-c",
                f"user.email={self.author_email}",
                "commit",
                "-m",
                commit_message,
            ]
        )

        if commit_result.returncode != 0:
            output = (commit_result.stderr or commit_result.stdout).strip()
            warning = f"git commit failed: {output}"
            logger.warning("git_commit_failed", extra={"step": "git", "job_id": str(job_id), "status": "failed"})
            return GitCommitResult(False, None, False, False, warning)

        sha_result = self._run_git(["rev-parse", "HEAD"])
        commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None

        push_attempted = False
        push_succeeded = False
        warning: str | None = None

        if self.enable_git_push:
            push_attempted = True
            push_result = self._run_git(["push"])
            push_succeeded = push_result.returncode == 0
            if not push_succeeded:
                warning = f"git push failed: {(push_result.stderr or push_result.stdout).strip()}"

        logger.info("git_commit_completed", extra={"step": "git", "job_id": str(job_id), "status": "ok"})
        return GitCommitResult(True, commit_sha, push_attempted, push_succeeded, warning)

    def _validate_allowed_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.repository_root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.generated_tests_root):
            raise ValueError("Only files under generated_tests are allowed for auto-commit")
        return resolved

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        result = subprocess.run(
            ["git", *args],
            cwd=str(self.repository_root),
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
            env=env,
        )
        logger.info(
            "git_command_executed",
            extra={
                "step": "git",
                "status": "ok" if result.returncode == 0 else "failed",
                "stdout": (result.stdout or "")[:500],
                "stderr": (result.stderr or "")[:500],
            },
        )
        return result
