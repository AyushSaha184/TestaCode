CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    input_mode TEXT NOT NULL CHECK (input_mode IN ('upload', 'paste')),
    original_filename TEXT NULL,
    detected_language TEXT NOT NULL,
    user_prompt TEXT NOT NULL,
    classified_intent JSONB NOT NULL DEFAULT '{}'::jsonb,
    analysis_text TEXT NULL,
    generated_test_code TEXT NULL,
    quality_score INT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    framework_used TEXT NULL,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncovered_areas JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS test_run_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    pass_count INT NOT NULL DEFAULT 0,
    fail_count INT NOT NULL DEFAULT 0,
    error_count INT NOT NULL DEFAULT 0,
    coverage_percentage NUMERIC NOT NULL DEFAULT 0,
    ci_run_url TEXT NULL,
    run_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_results JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_created_at_desc
    ON generation_jobs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_status
    ON generation_jobs (status);

CREATE INDEX IF NOT EXISTS idx_test_run_results_job_id_run_timestamp_desc
    ON test_run_results (job_id, run_timestamp DESC);
