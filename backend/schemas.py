from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ───────────────────────────────────────────────────────────────────

class InputMode(str, Enum):
    paste = "paste"
    upload = "upload"


class TargetLanguage(str, Enum):
    python = "python"
    javascript = "javascript"
    typescript = "typescript"
    java = "java"


# ─── Generation Request / Response ───────────────────────────────────────────

class GenerationRequest(BaseModel):
    """Request body for POST /generate."""
    input_mode: InputMode = Field(..., description="How the code was provided: paste or upload.")
    code_content: str = Field(..., description="The raw source code as a string.", max_length=100000)
    filename: Optional[str] = Field(None, description="Original filename (set when uploaded).")
    language: TargetLanguage = Field(..., description="Programming language of the source code.")
    user_prompt: str = Field(..., description="The user's free-text instruction for test generation.", max_length=5000)


class GenerationResponse(BaseModel):
    """Response body for POST /generate."""
    job_id: int
    generated_test_code: str
    quality_score: Optional[float] = None
    uncovered_areas: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    framework_used: Optional[str] = None


# ─── Job History Models ──────────────────────────────────────────────────────

class JobListItem(BaseModel):
    """Lightweight model for the history sidebar (GET /jobs)."""
    id: int
    timestamp: datetime
    input_mode: str
    original_filename: Optional[str] = None
    language: str
    quality_score: Optional[float] = None
    status: str

    class Config:
        from_attributes = True


class JobDetail(BaseModel):
    """Full detail model for a single job (GET /jobs/{job_id})."""
    id: int
    timestamp: datetime
    input_mode: str
    original_filename: Optional[str] = None
    language: str
    raw_prompt: Optional[str] = None
    classified_intent: Optional[str] = None
    generated_test_code: Optional[str] = None
    quality_score: Optional[float] = None
    status: str
    test_results: List["TestRunResultResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TestRunResultResponse(BaseModel):
    """Response model for individual test run results."""
    id: int
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    coverage_percentage: Optional[float] = None
    ci_run_url: Optional[str] = None
    run_timestamp: datetime

    class Config:
        from_attributes = True


# ─── Generation Options (used internally) ────────────────────────────────────

class GenerationOptions(BaseModel):
    """Internal options derived from the prompt intent classifier."""
    include_edge_cases: bool = True
    mock_external_dependencies: bool = True
    include_performance_tests: bool = False
    framework: str = "pytest"


# ─── Error ───────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
