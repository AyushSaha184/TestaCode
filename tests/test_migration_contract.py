from __future__ import annotations

from pathlib import Path


def test_generation_jobs_contract_columns_present_in_migrations() -> None:
    migrations_dir = Path("database/migrations")
    sql = "\n".join(
        (migrations_dir / name).read_text(encoding="utf-8")
        for name in [
            "001_phase_1_3_supabase.sql",
            "002_phase_4_ci_git.sql",
            "003_session_isolation.sql",
            "004_storage_and_contract_alignment.sql",
            "005_source_upload_artifacts.sql",
        ]
    ).lower()

    required_tokens = [
        "id uuid",
        "created_at timestamptz",
        "session_id",
        "input_mode",
        "original_filename",
        "detected_language",
        "user_prompt",
        "classified_intent",
        "analysis_text",
        "generated_test_code",
        "quality_score",
        "status",
        "framework_used",
        "warnings",
        "uncovered_areas",
        "source_file_path",
        "source_file_url",
        "output_test_path",
        "output_metadata_path",
        "output_test_url",
        "output_metadata_url",
        "auto_commit_enabled",
        "commit_sha",
        "workflow_name",
        "ci_status",
        "ci_conclusion",
        "ci_run_url",
        "ci_run_id",
        "ci_updated_at",
    ]

    for token in required_tokens:
        assert token in sql


def test_required_indexes_present_in_migrations() -> None:
    sql = Path("database/migrations/004_storage_and_contract_alignment.sql").read_text(encoding="utf-8").lower()

    assert "idx_generation_jobs_session_created_at_desc" in sql
    assert "idx_generation_jobs_status" in sql
    assert "idx_generation_jobs_ci_status" in sql
    assert "idx_test_run_results_job_id_run_timestamp_desc" in sql
