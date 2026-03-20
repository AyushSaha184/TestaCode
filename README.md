# AI Test Gen

AI Test Generation platform with FastAPI backend and React dashboard frontend.

## Project Structure
- backend/: FastAPI API, orchestration, repository, services
- frontend/: React + Vite TypeScript dashboard
- database/migrations/: SQL migrations for Supabase Postgres
- generated_tests/: deterministic generated test outputs

## Backend Quick Start
1. Create and activate virtual environment.
2. Install dependencies:
   - pip install -r requirements.txt
3. Run API:
   - uvicorn backend.app:app --reload --port 8000

## Frontend Quick Start
1. Go to frontend folder:
   - cd frontend
2. Copy .env.example to .env and set API URL.
3. Install and run:
   - npm install
   - npm run dev

## Frontend Env Vars
- VITE_API_BASE_URL (required)
- VITE_API_TIMEOUT_MS (optional)

## Backend Env Vars
- SUPABASE_DB_URL (required)
- SUPABASE_URL (required for Storage)
- SUPABASE_SERVICE_ROLE_KEY (required for private bucket uploads/signed URLs; backend only)
- SUPABASE_ANON_KEY (optional; never required by backend)
- SUPABASE_STORAGE_BUCKET (default: code-files)
- SUPABASE_STORAGE_PUBLIC (default: false)
- SUPABASE_SIGNED_URL_TTL_SECONDS (default: 3600)
- RENDER_EXTERNAL_URL (Render public backend URL)
- VERCEL_FRONTEND_URL (Vercel frontend URL for CORS)
- LOG_TO_FILE (default: true, set false on Render to use stdout-only logs)

## Supabase Storage Behavior
- Bucket default: `code-files`
- Artifact object paths:
  - `sessions/{session_id}/{language}/{feature_name}/test_{feature_name}.{ext}`
  - `sessions/{session_id}/{language}/{feature_name}/test_{feature_name}.json`
- Private bucket mode returns backend-generated signed URLs.
- Public bucket mode returns public URLs.

## Frontend Architecture Overview
- App shell with sidebar + header + responsive content grid
- Feature pages: generate, jobs, job detail, analytics, settings
- API integration through centralized Axios client and typed service wrappers
- Query/data caching through TanStack Query
- UI state persistence through Zustand
- Premium dark theme with Tailwind tokens and card-based layout

## Backend API Endpoints Used by Frontend
- POST /generate
- GET /jobs
- GET /jobs/{job_id}
- POST /jobs/{job_id}/rerun
- GET /jobs/{job_id}/status
