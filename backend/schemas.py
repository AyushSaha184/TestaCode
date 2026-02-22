from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class InputMode(str, Enum):
    natural_language = "natural_language"
    pasted_code = "pasted_code"
    file_upload = "file_upload"

class TargetLanguage(str, Enum):
    python = "python"
    javascript = "javascript"

class GenerationOptions(BaseModel):
    include_edge_cases: bool = True
    mock_external_dependencies: bool = True
    include_performance_tests: bool = False
    framework: str = "pytest"

class GenerationRequest(BaseModel):
    input_mode: InputMode = Field(..., description="The method of input provided by the user.")
    content: str = Field(..., description="The literal text or code to process.", max_length=100000)
    language: TargetLanguage = Field(..., description="The programming language of the target code.")
    options: GenerationOptions = Field(default_factory=GenerationOptions)

class GenerationResponse(BaseModel):
    job_id: int
    generated_test_code: str
    quality_score: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    detail: str
