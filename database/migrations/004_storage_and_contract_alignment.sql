ALTER TABLE generation_jobs
    ADD COLUMN IF NOT EXISTS output_test_url TEXT,
    ADD COLUMN IF NOT EXISTS output_metadata_url TEXT;

ALTER TABLE generation_jobs
    ALTER COLUMN classified_intent SET DEFAULT '{}'::jsonb,
    ALTER COLUMN warnings SET DEFAULT '[]'::jsonb,
    ALTER COLUMN uncovered_areas SET DEFAULT '[]'::jsonb,
    ALTER COLUMN auto_commit_enabled SET DEFAULT FALSE;

ALTER TABLE test_run_results
    ALTER COLUMN run_timestamp SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_generation_jobs_session_created_at_desc
    ON generation_jobs (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_status
    ON generation_jobs (status);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_ci_status
    ON generation_jobs (ci_status);

CREATE INDEX IF NOT EXISTS idx_test_run_results_job_id_run_timestamp_desc
    ON test_run_results (job_id, run_timestamp DESC);
