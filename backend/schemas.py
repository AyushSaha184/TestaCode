from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputMode(str, Enum):
	paste = "paste"
	upload = "upload"


class Language(str, Enum):
	python = "python"
	javascript = "javascript"
	typescript = "typescript"
	java = "java"


class JobStatus(str, Enum):
	queued = "queued"
	processing = "processing"
	completed = "completed"
	failed = "failed"


class TestType(str, Enum):
	unit = "unit"
	integration = "integration"
	edge = "edge"
	mixed = "mixed"


class TargetFramework(str, Enum):
	pytest = "pytest"
	unittest = "unittest"
	jest = "jest"
	mocha = "mocha"
	unspecified = "unspecified"


class ParameterMetadata(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	name: str
	type_annotation: str | None = None


class FunctionMetadata(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	name: str
	params: list[ParameterMetadata] = Field(default_factory=list)
	return_annotation: str | None = None
	docstring: str | None = None
	decorators: list[str] = Field(default_factory=list)
	dependency_hints: list[str] = Field(default_factory=list)


class IntentClassification(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	test_type: TestType = TestType.mixed
	target_scope: str = "all"
	target_framework: TargetFramework = TargetFramework.unspecified
	special_requirements: list[str] = Field(default_factory=list)
	confidence: float = 0.0

	@field_validator("confidence")
	@classmethod
	def clamp_confidence(cls, value: float) -> float:
		return max(0.0, min(1.0, value))


class GenerationRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	session_id: str
	input_mode: InputMode
	code_content: str
	filename: str | None = None
	language: Language
	user_prompt: str
	auto_commit_enabled: bool = False


class GenerationResponse(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	job_id: UUID
	generated_test_code: str
	quality_score: int
	uncovered_areas: list[str] = Field(default_factory=list)
	warnings: list[str] = Field(default_factory=list)
	framework_used: str
	source_file_path: str | None = None
	source_file_url: str | None = None
	output_test_path: str | None = None
	output_metadata_path: str | None = None
	output_test_url: str | None = None
	output_metadata_url: str | None = None
	commit_sha: str | None = None
	ci_status: str | None = None
	ci_conclusion: str | None = None
	ci_run_url: str | None = None
	ci_run_id: str | None = None


class JobSummary(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	id: UUID
	created_at: datetime
	status: JobStatus
	detected_language: Language
	quality_score: int | None = None
	framework_used: str | None = None
	ci_status: str | None = None


class TestRunResultModel(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	pass_count: int
	fail_count: int
	error_count: int
	coverage_percentage: float
	ci_run_url: str | None = None
	raw_results: dict[str, Any] | None = None


class JobDetail(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	id: UUID
	created_at: datetime
	input_mode: InputMode
	original_filename: str | None = None
	detected_language: Language
	user_prompt: str
	classified_intent: dict[str, Any]
	analysis_text: str | None = None
	generated_test_code: str | None = None
	quality_score: int | None = None
	status: JobStatus
	framework_used: str | None = None
	warnings: list[str] = Field(default_factory=list)
	uncovered_areas: list[str] = Field(default_factory=list)
	source_file_path: str | None = None
	source_file_url: str | None = None
	output_test_path: str | None = None
	output_metadata_path: str | None = None
	output_test_url: str | None = None
	output_metadata_url: str | None = None
	auto_commit_enabled: bool = False
	commit_sha: str | None = None
	workflow_name: str | None = None
	ci_status: str | None = None
	ci_conclusion: str | None = None
	ci_run_url: str | None = None
	ci_run_id: str | None = None
	ci_updated_at: datetime | None = None
	latest_run: TestRunResultModel | None = None


class RerunResult(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	original_job_id: UUID
	rerun_job_id: UUID
	status: JobStatus
	quality_score: int | None = None
	ci_status: str | None = None
	commit_sha: str | None = None


class JobStatusView(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	job_id: UUID
	status: JobStatus
	ci_status: str | None = None
	ci_conclusion: str | None = None
	ci_run_url: str | None = None
	ci_run_id: str | None = None
	ci_updated_at: datetime | None = None


class UnifiedContext(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	raw_code: str
	detected_language: Language
	function_metadata: list[FunctionMetadata]
	classified_intent: IntentClassification
	original_prompt: str
	warnings: list[str] = Field(default_factory=list)
