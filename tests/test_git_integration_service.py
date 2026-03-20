from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4

from backend.services.git_integration_service import GitIntegrationService


def test_git_integration_commit_flow(monkeypatch, tmp_path: Path) -> None:
    generated_dir = tmp_path / "generated_tests" / "python" / "feature"
    generated_dir.mkdir(parents=True)
    test_file = generated_dir / "test_feature.py"
    meta_file = generated_dir / "test_feature.json"
    test_file.write_text("ok", encoding="utf-8")
    meta_file.write_text("{}", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(cmd, cwd, text, capture_output, check, timeout, env):
        calls.append(cmd)
        if cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    service = GitIntegrationService(
        repository_root=str(tmp_path),
        generated_tests_dir="generated_tests",
        author_name="bot",
        author_email="bot@example.com",
        enable_git_push=False,
    )

    result = service.commit_generated_outputs(
        job_id=uuid4(),
        feature_name="feature",
        test_file_path="generated_tests/python/feature/test_feature.py",
        metadata_file_path="generated_tests/python/feature/test_feature.json",
    )

    assert result.committed is True
    assert result.commit_sha == "abc123"
    assert any(cmd[:2] == ["git", "add"] for cmd in calls)
    assert any("commit" in cmd for cmd in calls)


def test_git_integration_rejects_paths_outside_generated_tests(tmp_path: Path) -> None:
    service = GitIntegrationService(
        repository_root=str(tmp_path),
        generated_tests_dir="generated_tests",
        author_name="bot",
        author_email="bot@example.com",
        enable_git_push=False,
    )

    try:
        service._validate_allowed_path(str(tmp_path / "backend" / "app.py"))
    except ValueError as exc:
        assert "generated_tests" in str(exc)
    else:
        raise AssertionError("Expected ValueError for path outside generated_tests")
