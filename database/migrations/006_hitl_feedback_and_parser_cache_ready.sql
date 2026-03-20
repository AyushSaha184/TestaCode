CREATE TABLE IF NOT EXISTS generation_job_feedback (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	job_id UUID NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
	session_id TEXT NOT NULL,
	feedback_value TEXT NOT NULL CHECK (feedback_value IN ('up', 'down')),
	correction_text TEXT NULL,
	reviewer_notes TEXT NULL,
	detected_language TEXT NOT NULL,
	user_prompt_snapshot TEXT NOT NULL,
	generated_test_code_snapshot TEXT NULL,
	quality_score_snapshot INT NULL,
	framework_used_snapshot TEXT NULL,
	source_code_snapshot TEXT NULL,
	classified_intent_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT uq_generation_job_feedback_job_session UNIQUE (job_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_generation_job_feedback_session_created_at_desc
	ON generation_job_feedback (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generation_job_feedback_language_framework
	ON generation_job_feedback (detected_language, framework_used_snapshot);

CREATE INDEX IF NOT EXISTS idx_generation_job_feedback_value
	ON generation_job_feedback (feedback_value);
