from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import time

from backend.core.config import logger, settings
from backend.core.database import Base, engine, get_db
from backend.schemas import (
    GenerationRequest, GenerationResponse, ErrorResponse,
    JobListItem, JobDetail,
)
from backend.models import GenerationJob, TestRunResult
import backend.models  # Register models to SQLAlchemy

# ─── Database Initialization ─────────────────────────────────────────────────
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")
except Exception as e:
    logger.critical(f"Database initialization failed: {e}")

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Test Generator API",
    description="Backend for AI-Powered Test Case Generator",
    version="2.0.0",
)

# CORS configuration for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Middleware ───────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"Completed: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.2f}ms"
    )
    return response


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


# ─── POST /generate ──────────────────────────────────────────────────────────

@app.post(
    "/generate",
    response_model=GenerationResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def generate_tests(request: GenerationRequest, db: Session = Depends(get_db)):
    """
    Accepts a generation request (code + user prompt), runs the full pipeline
    (input processing → analysis → generation → validation → self-eval),
    persists the job to the database, and returns the result.
    """
    logger.info(
        f"Generation started | mode={request.input_mode.value} "
        f"| lang={request.language.value} | file={request.filename}"
    )

    # 1. Create a pending job record
    job = GenerationJob(
        input_mode=request.input_mode.value,
        original_filename=request.filename,
        language=request.language.value,
        raw_prompt=request.user_prompt,
        status="processing",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Job {job.id} created and set to 'processing'.")

    try:
        # 2. Run input processing
        from backend.input.handlers import process_code_input
        unified_context = process_code_input(
            code_content=request.code_content,
            language=request.language,
            user_prompt=request.user_prompt,
            filename=request.filename,
        )

        # 3. Run agent orchestrator
        from backend.agents.orchestrator import process_generation_flow
        agent_result = process_generation_flow(unified_context)

        # 4. Persist results to the job
        job.generated_test_code = agent_result.get("code", "")
        job.quality_score = agent_result.get("quality_score")
        job.classified_intent = agent_result.get("classified_intent")
        job.status = "completed" if agent_result["status"] == "success" else "failed"
        db.commit()

        logger.info(f"Job {job.id} completed | score={job.quality_score} | status={job.status}")

        return GenerationResponse(
            job_id=job.id,
            generated_test_code=agent_result.get("code", ""),
            quality_score=agent_result.get("quality_score"),
            uncovered_areas=agent_result.get("uncovered_areas", []),
            warnings=agent_result.get("warnings", []),
            framework_used=agent_result.get("framework_used"),
        )

    except Exception as e:
        job.status = "failed"
        db.commit()
        logger.error(f"Job {job.id} failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Generation failed: {str(e)}"},
        )


# ─── GET /jobs ────────────────────────────────────────────────────────────────

@app.get("/jobs", response_model=list[JobListItem])
def list_jobs(db: Session = Depends(get_db)):
    """Returns the history list for the sidebar, sorted most-recent-first."""
    jobs = db.query(GenerationJob).order_by(GenerationJob.timestamp.desc()).all()
    return [
        JobListItem(
            id=j.id,
            timestamp=j.timestamp,
            input_mode=j.input_mode,
            original_filename=j.original_filename,
            language=j.language,
            quality_score=j.quality_score,
            status=j.status,
        )
        for j in jobs
    ]


# ─── GET /jobs/{job_id} ──────────────────────────────────────────────────────

@app.get(
    "/jobs/{job_id}",
    response_model=JobDetail,
    responses={404: {"model": ErrorResponse}},
)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Returns full detail for a specific past job."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


# ─── POST /jobs/{job_id}/rerun ────────────────────────────────────────────────

@app.post(
    "/jobs/{job_id}/rerun",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def rerun_tests(job_id: int, db: Session = Depends(get_db)):
    """
    Re-executes the test file for a past job and stores the new run result.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    if not job.generated_test_code:
        raise HTTPException(status_code=400, detail="No generated test code to run for this job.")

    logger.info(f"Re-running tests for job {job_id}")

    try:
        from backend.agents.tools import write_test_file, run_pytest

        # Write the stored test code to a temp file and run it
        feature_name = (job.original_filename or "rerun").replace(".", "_")
        test_path = write_test_file(job.language, feature_name, job.generated_test_code)
        result = run_pytest(test_path)

        # Parse pass/fail counts from pytest output
        pass_count = 0
        fail_count = 0
        error_count = 0
        output_text = result.get("output", "")

        # Simple parsing of pytest summary line e.g. "3 passed, 1 failed, 1 error"
        import re
        summary_match = re.search(r"(\d+) passed", output_text)
        if summary_match:
            pass_count = int(summary_match.group(1))
        fail_match = re.search(r"(\d+) failed", output_text)
        if fail_match:
            fail_count = int(fail_match.group(1))
        error_match = re.search(r"(\d+) error", output_text)
        if error_match:
            error_count = int(error_match.group(1))

        # Store the run result
        run_result = TestRunResult(
            job_id=job.id,
            pass_count=pass_count,
            fail_count=fail_count,
            error_count=error_count,
        )
        db.add(run_result)
        db.commit()
        db.refresh(run_result)

        logger.info(f"Rerun for job {job_id}: passed={pass_count} failed={fail_count} errors={error_count}")

        return {
            "job_id": job_id,
            "run_id": run_result.id,
            "passed": result.get("passed", False),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "error_count": error_count,
            "output": output_text,
        }

    except Exception as e:
        logger.error(f"Rerun failed for job {job_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Test rerun failed: {str(e)}"},
        )


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
