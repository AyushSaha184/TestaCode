ALTER TABLE generation_jobs
    ADD COLUMN IF NOT EXISTS source_file_path TEXT,
    ADD COLUMN IF NOT EXISTS source_file_url TEXT;
