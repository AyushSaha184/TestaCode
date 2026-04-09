# AI-Test-Gen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-green.svg)](https://nodejs.org/)

AI-Test-Gen is an AI-powered test generation platform with a FastAPI backend and a React + TypeScript dashboard. It accepts pasted code or uploaded source files, classifies testing intent, generates tests using an LLM-driven chain, validates syntax, stores artifacts and metadata, and optionally auto-commits outputs to Git.

### Architecture Diagram

![Architecture Diagram](https://i.postimg.cc/9F9dGFD8/Architecture.png)

### Data Flow Diagram

![Data Flow Diagram](https://i.postimg.cc/G2sV0TLK/dataflow.png)

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/AI-Test-Gen.git
cd AI-Test-Gen

# 2. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and optional LLM keys

# 3. Start (Windows)
.\server.bat

# Or manually:
# Backend: uvicorn backend.app:app --reload --port 8000
# Frontend: cd frontend && npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## Live Architecture Focus

- Session-isolated generation requests via `X-Session-Id`
- Multi-stage backend pipeline: normalize -> parse -> classify -> analyze -> generate -> validate/correct -> self-evaluate -> persist
- Postgres-backed job lifecycle with migration-based schema contracts
- In-process TTL caches for parser results, intent classification, and idempotency
- Frontend dashboard for generation, job history, job detail, rerun, and analytics

## Table of Contents

- [Features](#features)
- [Supported Languages & Frameworks](#supported-languages--frameworks)
- [Project Structure](#project-structure)
- [How AI-Test-Gen Works](#how-ai-test-gen-works)
- [API Reference](#api-reference)
- [Installation](#installation)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Input modes**: Paste code directly or upload source files (`.py`, `.js`, `.ts`, `.java`)
- **Language detection**: Automatic language detection for pasted code
- **Smart parsing**: Python AST parser with caching; LLM-based parser for JS/TS
- **Intent classification**: Predicts test type, scope, framework, and confidence level
- **Multi-stage generation**: Analysis -> generation -> validation -> self-evaluation
- **Syntax validation**: Auto-corrects syntax errors (up to 3 retry attempts)
- **Job lifecycle**: Queued → processing → completed/failed with full state tracking
- **Artifact storage**: Test files + metadata JSON, locally or via Supabase
- **Rerun support**: Regenerate tests from saved code snapshot
- **Human feedback**: Thumbs up/down with optional correction notes
- **Session isolation**: Clean separation via `X-Session-Id` header
- **Idempotency**: Prevent duplicate generations with `Idempotency-Key`
- **Modern UI**: React 19, Monaco editor, code viewer, analytics dashboard

## Supported Languages & Frameworks

| Language | Test Framework | Parser |
|----------|---------------|--------|
| Python | pytest | AST-based |
| JavaScript | Jest | LLM JSON schema |
| TypeScript | Jest | LLM JSON schema |
| Java | JUnit | LLM JSON schema |

## Project Structure

### Core Generation Pipeline

- **Input normalization** supports two modes:
   - `paste`: source code in form data
   - `upload`: UTF-8 source file upload with strict extension validation (`.py`, `.js`, `.ts`, `.java`)
- **Language detection fallback** for paste mode when language is omitted.
- **Python AST parser** extracts function metadata, signatures, decorators, and dependency hints.
- **Python AST-based parser caching** uses canonical AST hashing (comment/format-insensitive, docstring-sensitive) to improve cache reuse without hiding metadata changes.
- **Non-Python parser caching fallback** keeps existing raw-content hashing for JavaScript/TypeScript/Java until a robust local AST path is added.
- **JavaScript/TypeScript parser** uses a fast LLM JSON schema parser for function metadata.
- **Intent classifier** predicts test type, target scope, preferred framework, and confidence.
- **Prompt chain** performs:
   - analysis generation
   - test generation
   - syntax validation + auto-correction retries (up to 3 attempts)
   - self-evaluation with quality score and uncovered areas

### Persistence and Artifact Lifecycle

- **Job persistence** in Postgres with status states: `queued`, `processing`, `completed`, `failed`.
- **Artifact writing** generates:
   - test file
   - metadata JSON
- **Supabase Storage integration** uploads artifacts and returns signed/public URLs.
- **Source upload support** persists original uploaded source file path/URL.
- **Per-job run stats** recorded in `test_run_results`.
- **Rerun support** regenerates tests from saved code snapshot and prior intent context.
- **Human-in-the-loop feedback** stores thumbs up/down plus optional correction and reviewer notes in `generation_job_feedback` for future dataset export.

### Reliability and Guardrails

- **Idempotency key support** via request header `Idempotency-Key` scoped by session.
- **Session isolation** in API listing and job retrieval.
- **Request context middleware** emits `X-Request-ID` and latency logs.
- **Structured exception handling** for app-level and unhandled failures.
- **Fallback behavior when LLM is disabled** enables deterministic degraded operation.

### DevEx and UI

- **Modern frontend stack**: React 19, Vite, TypeScript, TanStack Query, Zustand, Monaco editor.
- **Pages**: Generate, Jobs, Job Detail, Analytics, Settings placeholder.
- **Rich outputs**: code viewer, warning badges, uncovered area tags, artifact links, CI status.
- **One-command local startup on Windows** via `server.bat`.

## Project Structure

```text
.
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py            # End-to-end generation lifecycle coordinator
│   │   ├── chains.py                  # Analysis/generation/validation/self-eval chain
│   │   ├── llm_gateway.py             # Provider gateway + fallback + retry
│   │   ├── prompts.py                 # Prompt templates by intent/test type
│   │   └── tools.py                   # Language syntax validation helpers
│   ├── api/
│   │   └── routes.py                  # /generate, /jobs, /jobs/{id}, /rerun, /status
│   ├── core/
│   │   ├── config.py                  # Settings and env parsing
│   │   ├── database.py                # psycopg-backed DB client
│   │   ├── cache.py                   # In-memory TTL caches
│   │   ├── middleware.py              # Request ID + latency middleware
│   │   ├── exceptions.py              # AppError + global handlers
│   │   └── logger.py                  # Structured logging setup
│   ├── input/
│   │   ├── normalizer.py              # Form/input normalization and guardrails
│   │   ├── handlers.py                # Unified context construction
│   │   ├── parsers.py                 # Python AST parser + parser cache
│   │   ├── js_parser.py               # JS/TS LLM parser
│   │   └── intent_classifier.py       # Intent classification with confidence warnings
│   ├── repositories/
│   │   └── generation_repository.py   # SQL persistence for jobs and test runs
│   ├── services/
│   │   └── file_output_service.py     # Atomic local file writes
│   ├── app.py                         # FastAPI factory
│   ├── bootstrap.py                   # DI wiring and singleton providers
│   ├── main.py                        # Export app entrypoint
│   └── schemas.py                     # Pydantic contracts
├── database/
│   └── migrations/
│       ├── 001_phase_1_3_supabase.sql
│       ├── 002_phase_4_ci_git.sql
│       ├── 003_session_isolation.sql
│       ├── 004_storage_and_contract_alignment.sql
│       ├── 005_source_upload_artifacts.sql
│       └── 006_hitl_feedback_and_parser_cache_ready.sql
├── frontend/
│   ├── src/
│   │   ├── app/                       # Routing and providers
│   │   ├── features/                  # generate, jobs, job-detail, analytics, settings
│   │   ├── services/                  # Axios client + API wrappers
│   │   ├── hooks/                     # TanStack Query hooks
│   │   ├── components/                # Layout and shared components
│   │   ├── store/                     # Zustand UI state
│   │   └── types/                     # API contracts
│   ├── package.json
│   └── vite.config.ts
├── generated_tests/                   # Generated local artifacts
├── tests/                             # Backend and contract test suite
├── server.bat                         # Windows local launcher
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── requirements.txt
```

## API Reference

### Generation Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate` | Generate tests from pasted code or uploaded file |
| `GET` | `/jobs` | List jobs by session with pagination |
| `GET` | `/jobs/{job_id}` | Fetch full job detail, artifacts, and latest run |
| `POST` | `/jobs/{job_id}/rerun` | Regenerate tests from prior job snapshot |
| `GET` | `/jobs/{job_id}/status` | Lightweight status endpoint |
| `POST` | `/jobs/{job_id}/feedback` | Submit or update current session feedback for a job |
| `GET` | `/jobs/{job_id}/feedback` | Retrieve current session feedback for a job |
| `GET` | `/health` | API + DB health check |

### Required Header

- `X-Session-Id`: required on generation/job endpoints

### Optional Header

- `Idempotency-Key`: prevents duplicate generation per session

## Installation

### Prerequisites

- Python 3.10+
- Node.js 20+
- PostgreSQL (required for runtime DB)
- Optional: LLM API keys

### 1) Backend Setup

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Frontend Setup

```bash
cd frontend
npm install
```

### 3) Environment Configuration

```bash
cp .env.example .env
# Then edit .env values
```

### 4) Run Locally

```bash
.\server.bat
```

## Configuration

### Backend Environment Variables 

```bash
# Core
APP_ENV=development
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
ALLOWED_ORIGINS=http://localhost:5173

# LLM
LLM_ENABLED=
LLM_API_KEY=
CEREBRAS_API_KEY=
GOOGLE_API_KEY=
LLM_FAST_MODEL=gemini-3.0-flash-preview
LLM_FAST_FALLBACK_MODEL=gemini-2.5-flash
LLM_STRONG_MODEL=qwen-3-235b-a22b-instruct-2507
LLM_TIMEOUT_SECONDS=25
LLM_MAX_RETRIES=3

# Caching
PARSER_CACHE_TTL_SECONDS=600
INTENT_CACHE_TTL_SECONDS=600
IDEMPOTENCY_TTL_SECONDS=3600
```

### Frontend Environment Variables

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=30000
```

## Testing

Run backend tests:

```bash
pytest -q
```

Representative coverage includes:

- request normalization and validation contracts
- generate endpoint contract
- job detail/status contract
- repository artifact field mapping
- migration schema/index contract
- git integration path safety and commit flow
- storage service URL/upload behavior

## Deployment

### Render

- `render.yaml` defines a Python web service using `uvicorn backend.app:app`.
- Health check path: `/health`.

### Docker

This repository uses a multi-stage `Dockerfile` that builds both backend and frontend.

```bash
docker build -t ai-test-gen .
docker run -p 8000:8000 -p 5173:5173 ai-test-gen
```

Or use the provided `docker-compose.yml`:

```bash
docker-compose up --build
```

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes** and add tests if applicable
4. **Run tests**: `pytest -q`
5. **Commit** with a clear message: `git commit -m "Add feature X"`
6. **Push** to your fork: `git push origin feature/your-feature`
7. **Open a Pull Request**

### Development Workflow

- Backend tests are in `tests/`
- Run `pytest -q` before submitting PRs
- Ensure environment variables are documented in `.env.example`
- Follow the existing code structure in `backend/` and `frontend/`

## Troubleshooting

### DATABASE_URL missing

`DatabaseClient` requires `DATABASE_URL` at runtime. Set it in `.env` before starting backend.

### 422 on /generate

Common causes:

- missing `X-Session-Id`
- `input_mode=upload` without `upload_file`
- unsupported extension
- non-UTF8 uploaded file

### JS/TS validation failures

JS/TS syntax checks rely on `node --check`. Ensure Node.js is installed and available on PATH.

### LLM disabled output quality

If `LLM_ENABLED=false`, the system runs in fallback mode and generated output quality is intentionally limited.

### Artifact URLs not returned

Set all storage vars:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

Otherwise, artifacts are written locally and URL fields may be empty.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
