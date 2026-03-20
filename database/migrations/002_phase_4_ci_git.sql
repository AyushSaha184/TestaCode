ALTER TABLE generation_jobs
    ADD COLUMN IF NOT EXISTS commit_sha TEXT,
    ADD COLUMN IF NOT EXISTS ci_status TEXT,
    ADD COLUMN IF NOT EXISTS ci_conclusion TEXT,
    ADD COLUMN IF NOT EXISTS ci_run_url TEXT,
    ADD COLUMN IF NOT EXISTS ci_run_id TEXT,
    ADD COLUMN IF NOT EXISTS ci_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS workflow_name TEXT,
    ADD COLUMN IF NOT EXISTS output_test_path TEXT,
    ADD COLUMN IF NOT EXISTS output_metadata_path TEXT,
    ADD COLUMN IF NOT EXISTS auto_commit_enabled BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_generation_jobs_commit_sha
    ON generation_jobs (commit_sha);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_ci_status
    ON generation_jobs (ci_status);
