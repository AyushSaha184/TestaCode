ALTER TABLE generation_jobs
    ADD COLUMN IF NOT EXISTS session_id TEXT;

UPDATE generation_jobs
SET session_id = 'legacy'
WHERE session_id IS NULL;

ALTER TABLE generation_jobs
    ALTER COLUMN session_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generation_jobs_session_created_at_desc
    ON generation_jobs (session_id, created_at DESC);
