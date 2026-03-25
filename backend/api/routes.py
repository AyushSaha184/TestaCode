from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile

from backend.agents.orchestrator import GenerationOrchestrator
from backend.bootstrap import get_orchestrator, get_repository, get_storage_service
from backend.core.exceptions import AppError
from backend.util.logger import get_logger
from backend.core.config import get_settings
from backend.input.normalizer import normalize_generation_request
from backend.repositories.generation_repository import GenerationRepository
from backend.services.supabase_storage_service import SupabaseStorageService
from backend.schemas import (
    GenerationResponse,
    JobDetail,
    JobFeedbackRequest,
    JobFeedbackResponse,
    JobStatusView,
    JobSummary,
    RerunResult,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate", response_model=GenerationResponse)
async def generate_tests(
    input_mode: Annotated[str, Form(...)],
    user_prompt: Annotated[str, Form(...)],
    session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
    code_content: Annotated[str | None, Form()] = None,
    filename: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    auto_commit_enabled: Annotated[bool | None, Form()] = None,
    upload_file: UploadFile | None = File(default=None),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    orchestrator: GenerationOrchestrator = Depends(get_orchestrator),
) -> GenerationResponse:
    settings = get_settings()
    request, warnings = await normalize_generation_request(
        settings=settings,
        session_id=session_id,
        input_mode=input_mode,
        user_prompt=user_prompt,
        code_content=code_content,
        filename=filename,
        language=language,
        upload_file=upload_file,
        auto_commit_enabled=auto_commit_enabled,
    )
    logger.info("generate_request_received", extra={"step": "request", "status": "ok"})
    return orchestrator.generate(request, warnings, idempotency_key=idempotency_key)


@router.get("/jobs", response_model=list[JobSummary])
def list_jobs(
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    repository: GenerationRepository = Depends(get_repository),
) -> list[JobSummary]:
    return repository.list_jobs(session_id=session_id, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(
    job_id: UUID,
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    repository: GenerationRepository = Depends(get_repository),
    storage_service: SupabaseStorageService | None = Depends(get_storage_service),
) -> JobDetail:
    job = repository.get_job(job_id, session_id=session_id)
    if not job:
        raise AppError("Job not found", status_code=404)

    if storage_service and storage_service.is_configured():
        try:
            if job.source_file_path:
                job.source_file_url = storage_service.resolve_object_url(job.source_file_path)
            if job.output_test_path:
                job.output_test_url = storage_service.resolve_object_url(job.output_test_path)
            if job.output_metadata_path:
                job.output_metadata_url = storage_service.resolve_object_url(job.output_metadata_path)
        except Exception as exc:
            logger.warning(
                "storage_url_resolution_failed",
                extra={"step": "storage", "job_id": str(job_id), "status": "failed", "error": str(exc)[:500]},
            )
            job.warnings = [*job.warnings, "Artifact URL refresh is temporarily unavailable"]
    return job


@router.post("/jobs/{job_id}/rerun", response_model=RerunResult)
def rerun_job(
    job_id: UUID,
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    orchestrator: GenerationOrchestrator = Depends(get_orchestrator),
) -> RerunResult:
    logger.info("rerun_requested", extra={"step": "rerun", "job_id": str(job_id), "status": "processing"})
    return orchestrator.rerun(job_id, session_id=session_id)


@router.get("/jobs/{job_id}/status", response_model=JobStatusView)
def get_job_status(
    job_id: UUID,
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    orchestrator: GenerationOrchestrator = Depends(get_orchestrator),
) -> JobStatusView:
    return orchestrator.get_status(job_id, session_id=session_id)


@router.post("/jobs/{job_id}/feedback", response_model=JobFeedbackResponse)
def submit_job_feedback(
    job_id: UUID,
    payload: JobFeedbackRequest,
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    repository: GenerationRepository = Depends(get_repository),
) -> JobFeedbackResponse:
    if not repository.get_job_record(job_id, session_id=session_id):
        raise AppError("Job not found", status_code=404)
    return repository.upsert_job_feedback(job_id=job_id, session_id=session_id, payload=payload)


@router.get("/jobs/{job_id}/feedback", response_model=JobFeedbackResponse | None)
def get_job_feedback(
    job_id: UUID,
    session_id: Annotated[str, Header(alias="X-Session-Id")],
    repository: GenerationRepository = Depends(get_repository),
) -> JobFeedbackResponse | None:
    if not repository.get_job_record(job_id, session_id=session_id):
        raise AppError("Job not found", status_code=404)
    return repository.get_job_feedback(job_id=job_id, session_id=session_id)
