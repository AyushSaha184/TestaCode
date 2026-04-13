from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from backend.core.database import DatabaseClient
from backend.schemas import (
    FeedbackValue,
    GenerationRequest,
    InputMode,
    JobDetail,
    JobFeedbackRequest,
    JobFeedbackResponse,
    JobStatus,
    JobSummary,
    Language,
    PositiveFeedbackExample,
    TestRunResultModel,
)


class GenerationRepository:
    def __init__(self, db: DatabaseClient) -> None:
        self.db = db

    def create_job(
        self,
        payload: GenerationRequest,
        status: JobStatus = JobStatus.queued,
        idempotency_key: str | None = None,
    ) -> UUID:
        if idempotency_key:
            existing = self.db.fetchone(
                """
                SELECT id FROM generation_jobs
                WHERE session_id = %s
                  AND idempotency_key = %s
                  AND status IN ('completed', 'processing', 'queued')
                LIMIT 1
                """,
                (payload.session_id, idempotency_key),
            )
            if existing:
                return existing["id"]

        job_id = uuid4()
        self.db.execute(
            """
            INSERT INTO generation_jobs (
                id, session_id, input_mode, original_filename, detected_language,
                user_prompt, classified_intent, status, idempotency_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                job_id,
                payload.session_id,
                payload.input_mode.value,
                payload.filename,
                payload.language.value,
                payload.user_prompt,
                "{}",
                status.value,
                idempotency_key,
            ),
        )
        return job_id

    def update_job_processing(self, job_id: UUID) -> None:
        self.db.execute(
            "UPDATE generation_jobs SET status = %s WHERE id = %s",
            (JobStatus.processing.value, job_id),
        )

    def update_job_completed(
        self,
        job_id: UUID,
        classified_intent: dict[str, Any],
        analysis_text: str,
        generated_test_code: str,
        quality_score: int,
        framework_used: str,
        warnings: list[str],
        uncovered_areas: list[str],
    ) -> None:
        self.db.execute(
            """
            UPDATE generation_jobs
            SET
                status = %s,
                classified_intent = %s::jsonb,
                analysis_text = %s,
                generated_test_code = %s,
                quality_score = %s,
                framework_used = %s,
                warnings = %s::jsonb,
                uncovered_areas = %s::jsonb
            WHERE id = %s
            """,
            (
                JobStatus.completed.value,
                _to_json(classified_intent),
                analysis_text,
                generated_test_code,
                quality_score,
                framework_used,
                _to_json(warnings),
                _to_json(uncovered_areas),
                job_id,
            ),
        )

    def update_job_failed(self, job_id: UUID, warnings: list[str]) -> None:
        self.db.execute(
            "UPDATE generation_jobs SET status = %s, warnings = %s::jsonb WHERE id = %s",
            (JobStatus.failed.value, _to_json(warnings), job_id),
        )

    def append_warning(self, job_id: UUID, warning: str) -> None:
        self.db.execute(
            """
            UPDATE generation_jobs
            SET warnings = COALESCE(warnings, '[]'::jsonb) || jsonb_build_array(%s)
            WHERE id = %s
            """,
            (warning, job_id),
        )

    def update_file_outputs(
        self,
        job_id: UUID,
        source_file_path: str | None,
        output_test_path: str | None,
        output_metadata_path: str | None,
    ) -> None:
        self.db.execute(
            """
            UPDATE generation_jobs
            SET source_file_path = %s,
                output_test_path = %s,
                output_metadata_path = %s
            WHERE id = %s
            """,
            (
                source_file_path,
                output_test_path,
                output_metadata_path,
                job_id,
            ),
        )

    def get_job_record(self, job_id: UUID, session_id: str) -> dict[str, Any] | None:
        return self.db.fetchone(
            "SELECT * FROM generation_jobs WHERE id = %s AND session_id = %s",
            (job_id, session_id),
        )

    def get_job(self, job_id: UUID, session_id: str) -> JobDetail | None:
        row = self.db.fetchone(
            "SELECT * FROM generation_jobs WHERE id = %s AND session_id = %s",
            (job_id, session_id),
        )
        if not row:
            return None

        latest_run_raw = self.db.fetchone(
            """
            SELECT pass_count, fail_count, error_count, coverage_percentage, raw_results
            FROM test_run_results
            WHERE job_id = %s
            ORDER BY run_timestamp DESC
            LIMIT 1
            """,
            (job_id,),
        )

        latest_run = None
        if latest_run_raw:
            latest_run = TestRunResultModel(
                pass_count=latest_run_raw["pass_count"],
                fail_count=latest_run_raw["fail_count"],
                error_count=latest_run_raw["error_count"],
                coverage_percentage=float(latest_run_raw["coverage_percentage"]),
                raw_results=latest_run_raw.get("raw_results"),
            )

        return JobDetail(
            id=row["id"],
            created_at=row["created_at"],
            input_mode=InputMode(row["input_mode"]),
            original_filename=row["original_filename"],
            detected_language=Language(row["detected_language"]),
            user_prompt=row["user_prompt"],
            classified_intent=row.get("classified_intent") or {},
            analysis_text=row.get("analysis_text"),
            generated_test_code=row.get("generated_test_code"),
            quality_score=row.get("quality_score"),
            status=JobStatus(row["status"]),
            framework_used=row.get("framework_used"),
            warnings=(row.get("warnings") or []),
            uncovered_areas=(row.get("uncovered_areas") or []),
            source_file_path=row.get("source_file_path"),
            output_test_path=row.get("output_test_path"),
            output_metadata_path=row.get("output_metadata_path"),
            latest_run=latest_run,
        )

    def list_jobs(self, session_id: str, page: int, page_size: int) -> list[JobSummary]:
        offset = (page - 1) * page_size
        rows = self.db.fetchall(
            """
            SELECT id, created_at, status, detected_language, quality_score, framework_used
            FROM generation_jobs
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (session_id, page_size, offset),
        )
        return [
            JobSummary(
                id=row["id"],
                created_at=row["created_at"],
                status=JobStatus(row["status"]),
                detected_language=Language(row["detected_language"]),
                quality_score=row["quality_score"],
                framework_used=row["framework_used"],
            )
            for row in rows
        ]

    def healthcheck(self) -> datetime:
        row = self.db.fetchone("SELECT NOW() AS ts")
        if not row:
            raise RuntimeError("Database health check failed")
        return row["ts"]

    def upsert_job_feedback(
        self, job_id: UUID, session_id: str, payload: JobFeedbackRequest
    ) -> JobFeedbackResponse:
        snapshot = self.db.fetchone(
            """
            SELECT detected_language, user_prompt, generated_test_code, quality_score, framework_used, classified_intent
            FROM generation_jobs
            WHERE id = %s AND session_id = %s
            """,
            (job_id, session_id),
        )
        if not snapshot:
            raise RuntimeError("Cannot upsert feedback for missing job")

        row = self.db.fetchone(
            """
            INSERT INTO generation_job_feedback (
                id,
                job_id,
                session_id,
                feedback_value,
                correction_text,
                reviewer_notes,
                detected_language,
                user_prompt_snapshot,
                generated_test_code_snapshot,
                quality_score_snapshot,
                framework_used_snapshot,
                source_code_snapshot,
                classified_intent_snapshot
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            ON CONFLICT (job_id, session_id)
            DO UPDATE SET
                feedback_value = EXCLUDED.feedback_value,
                correction_text = EXCLUDED.correction_text,
                reviewer_notes = EXCLUDED.reviewer_notes,
                detected_language = EXCLUDED.detected_language,
                user_prompt_snapshot = EXCLUDED.user_prompt_snapshot,
                generated_test_code_snapshot = EXCLUDED.generated_test_code_snapshot,
                quality_score_snapshot = EXCLUDED.quality_score_snapshot,
                framework_used_snapshot = EXCLUDED.framework_used_snapshot,
                source_code_snapshot = EXCLUDED.source_code_snapshot,
                classified_intent_snapshot = EXCLUDED.classified_intent_snapshot,
                updated_at = NOW()
            RETURNING *
            """,
            (
                uuid4(),
                job_id,
                session_id,
                payload.feedback_value.value,
                payload.correction_text,
                payload.reviewer_notes,
                snapshot["detected_language"],
                snapshot["user_prompt"],
                snapshot.get("generated_test_code"),
                snapshot.get("quality_score"),
                snapshot.get("framework_used"),
                None,
                _to_json(snapshot.get("classified_intent") or {}),
            ),
        )
        if not row:
            raise RuntimeError("Failed to persist job feedback")
        return _row_to_job_feedback(row)

    def get_job_feedback(
        self, job_id: UUID, session_id: str
    ) -> JobFeedbackResponse | None:
        row = self.db.fetchone(
            "SELECT * FROM generation_job_feedback WHERE job_id = %s AND session_id = %s",
            (job_id, session_id),
        )
        if not row:
            return None
        return _row_to_job_feedback(row)

    def get_recent_positive_feedback_examples(
        self,
        *,
        session_id: str,
        language: Language,
        framework_used: str | None,
        limit: int = 5,
    ) -> list[PositiveFeedbackExample]:
        framework_clause = "AND framework_used_snapshot = %s" if framework_used else ""
        params: list[Any] = [session_id, language.value]
        if framework_used:
            params.append(framework_used)
        params.append(limit)

        rows = self.db.fetchall(
            f"""
            SELECT job_id, detected_language, framework_used_snapshot, generated_test_code_snapshot,
                   correction_text, reviewer_notes, quality_score_snapshot, created_at
            FROM generation_job_feedback
            WHERE session_id = %s
              AND detected_language = %s
              AND feedback_value = 'up'
              {framework_clause}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return [
            PositiveFeedbackExample(
                job_id=row["job_id"],
                detected_language=Language(row["detected_language"]),
                framework_used_snapshot=row.get("framework_used_snapshot"),
                generated_test_code_snapshot=row.get("generated_test_code_snapshot"),
                correction_text=row.get("correction_text"),
                reviewer_notes=row.get("reviewer_notes"),
                quality_score_snapshot=row.get("quality_score_snapshot"),
                created_at=row["created_at"],
            )
            for row in rows
        ]


def _to_json(value: Any) -> str:
    return json.dumps(value, default=str)


def _row_to_job_feedback(row: dict[str, Any]) -> JobFeedbackResponse:
    return JobFeedbackResponse(
        id=row["id"],
        job_id=row["job_id"],
        session_id=row["session_id"],
        feedback_value=FeedbackValue(row["feedback_value"]),
        correction_text=row.get("correction_text"),
        reviewer_notes=row.get("reviewer_notes"),
        detected_language=Language(row["detected_language"]),
        user_prompt_snapshot=row["user_prompt_snapshot"],
        generated_test_code_snapshot=row.get("generated_test_code_snapshot"),
        quality_score_snapshot=row.get("quality_score_snapshot"),
        framework_used_snapshot=row.get("framework_used_snapshot"),
        source_code_snapshot=row.get("source_code_snapshot"),
        classified_intent_snapshot=row.get("classified_intent_snapshot") or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
